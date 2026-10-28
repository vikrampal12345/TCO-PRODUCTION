from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from backend.core.bootstrap import build_default_registry
from backend.workflows.assessment_delivery import AssessmentDeliveryWorkflow
from backend.tools.classroom import ClassroomTool, ClassroomToolError

router = APIRouter(
    prefix="/api/v1/assessment-workflows",
    tags=["Assessment Workflow"],
)

@router.get("/classroom/courses")
def list_classroom_courses() -> dict[str, Any]:
    try:
        courses = ClassroomTool().list_courses()
    except ClassroomToolError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"courses": courses}

_lock = RLock()
_states: dict[str, dict[str, Any]] = {}
_delivery_workflow: AssessmentDeliveryWorkflow | None = None
_STATE_DIRECTORY = Path(__file__).resolve().parents[2] / "data" / "assessment_workflows"


_DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "tco.db"


def _record_workflow_assessment(
    workflow_id: str,
    assessment_id: int,
) -> None:
    """Persist the relation between a published workflow and its assessment."""
    with sqlite3.connect(_DATABASE_PATH, timeout=10) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS assessment_workflow_links (
                workflow_id TEXT PRIMARY KEY,
                assessment_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            INSERT INTO assessment_workflow_links (workflow_id, assessment_id)
            VALUES (?, ?)
            ON CONFLICT(workflow_id)
            DO UPDATE SET assessment_id = excluded.assessment_id
            """,
            (workflow_id, int(assessment_id)),
        )


def _recover_published_state(workflow_id: str) -> dict[str, Any] | None:
    """Recover a previously published workflow using its saved DB mapping."""
    if not _DATABASE_PATH.exists():
        return None

    with sqlite3.connect(_DATABASE_PATH, timeout=10) as connection:
        connection.row_factory = sqlite3.Row

        try:
            link = connection.execute(
                """
                SELECT assessment_id
                FROM assessment_workflow_links
                WHERE workflow_id = ?
                """,
                (workflow_id,),
            ).fetchone()
        except sqlite3.OperationalError:
            return None

        if link is None:
            return None

        assessment = connection.execute(
            "SELECT * FROM assessments WHERE id = ?",
            (int(link["assessment_id"]),),
        ).fetchone()

        if assessment is None:
            return None

        assessment = dict(assessment)

        if (
            str(assessment.get("status", "")).lower() != "published"
            or not assessment.get("form_id")
            or not assessment.get("responder_url")
        ):
            return None

        question_rows = connection.execute(
            """
            SELECT *
            FROM assessment_questions
            WHERE assessment_id = ?
            ORDER BY question_number
            """,
            (int(link["assessment_id"]),),
        ).fetchall()

        questions = []
        for row in question_rows:
            question = dict(row)
            raw_options = question.pop("options_json", "[]")
            try:
                question["options"] = json.loads(raw_options or "[]")
            except (TypeError, json.JSONDecodeError):
                question["options"] = []
            questions.append(question)

    topic = assessment.get("topic") or assessment.get("title") or "Assessment"
    question_count = int(assessment.get("question_count") or len(questions))
    total_marks = int(assessment.get("total_marks") or 0)
    class_level = str(assessment.get("class_level") or "")
    section = str(assessment.get("section") or "")

    return {
        "workflow_id": workflow_id,
        "request_id": workflow_id,
        "conversation_id": workflow_id,
        "teacher_id": str(assessment.get("created_by") or ""),
        "school_id": str(assessment.get("school_id") or ""),
        "teacher_request": f"Recovered published assessment: {topic}",
        "intent": "assessment",
        "language": "english",
        "topic": topic,
        "title": assessment.get("title") or topic,
        "subject": assessment.get("subject") or "",
        "chapter": assessment.get("chapter") or "",
        "class_level": class_level,
        "student_class_level": class_level,
        "section": section,
        "question_count": question_count,
        "marks": total_marks,
        "total_marks": total_marks,
        "questions": questions,
        "assessment_id": int(assessment["id"]),
        "form_id": assessment["form_id"],
        "responder_url": assessment["responder_url"],
        "status": "assessment_form_published",
        "approval_status": "approved",
        "publication_status": "published",
        "metadata": {
            "mode": assessment.get("generation_mode") or "general_knowledge",
            "recovered_from_database": True,
        },
        "recovered_from_database": True,
        "class_level_mapping_missing": not bool(class_level and section),
    }


Mode = Literal[
    "general_knowledge",
    "teacher_file",
    "classroom",
    "web_search",
]


class GenerateAssessmentRequest(BaseModel):
    teacher_request: str = Field(min_length=1, max_length=10000)
    teacher_id: str = Field(min_length=1, max_length=200)
    school_id: str = Field(min_length=1, max_length=200)
    topic: str = Field(min_length=1, max_length=500)
    question_count: int = Field(ge=1, le=200)
    marks: int = Field(ge=1, le=10000)
    mode: Mode = "general_knowledge"
    subject: str = ""
    chapter: str = ""
    class_level: str = ""
    student_class_level: str = ""
    section: str = ""
    classroom_course_id: str = ""
    conversation_id: str = ""


class RegenerateRequest(BaseModel):
    feedback: str = Field(default="", max_length=4000)


class SourceApprovalRequest(BaseModel):
    selected_url: str = Field(min_length=8, max_length=3000)
    approval_comment: str = Field(default="", max_length=2000)


def _get_workflow() -> AssessmentDeliveryWorkflow:
    global _delivery_workflow

    if _delivery_workflow is None:
        _delivery_workflow = AssessmentDeliveryWorkflow(
            build_default_registry(),
            max_review_attempts=3,
        )

    return _delivery_workflow




def _hydrate_published_state(state: dict[str, Any]) -> dict[str, Any]:
    """Refresh persisted publication fields from the authoritative SQLite row."""
    assessment_id = state.get("assessment_id")
    if not assessment_id or not _DATABASE_PATH.exists():
        return state

    try:
        with sqlite3.connect(
            _DATABASE_PATH.resolve().as_uri() + "?mode=ro",
            uri=True,
            timeout=10,
        ) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """
                SELECT id, title, topic, school_id, created_by,
                       class_level, section, question_count, total_marks,
                       form_id, responder_url, status, generation_mode
                FROM assessments
                WHERE id = ?
                """,
                (int(assessment_id),),
            ).fetchone()
    except (sqlite3.Error, ValueError, TypeError):
        return state

    if row is None:
        return state

    record = dict(row)
    if (
        str(record.get("status", "")).lower() != "published"
        or not record.get("form_id")
        or not record.get("responder_url")
    ):
        return state

    # Do not attach a database assessment if this workflow points to another Form.
    existing_form_id = state.get("form_id")
    if existing_form_id and existing_form_id != record["form_id"]:
        return state

    state["assessment_id"] = int(record["id"])
    state["form_id"] = record["form_id"]
    state["responder_url"] = record["responder_url"]
    state["question_count"] = int(record.get("question_count") or 0)
    state["marks"] = int(record.get("total_marks") or 0)
    state["total_marks"] = int(record.get("total_marks") or 0)
    state["title"] = record.get("title") or state.get("title") or ""
    state["topic"] = record.get("topic") or state.get("topic") or ""
    state["school_id"] = record.get("school_id") or state.get("school_id") or ""
    state["teacher_id"] = record.get("created_by") or state.get("teacher_id") or ""
    state["class_level"] = record.get("class_level") or ""
    state["student_class_level"] = record.get("class_level") or ""
    state["section"] = record.get("section") or ""
    state["publication_status"] = "published"
    state["database_assessment_synced"] = True
    state["class_level_mapping_missing"] = not bool(
        record.get("class_level") and record.get("section")
    )
    state.setdefault("approval_status", "approved")
    # Restore the saved student-delivery cohort from SQLite.
    try:
        _cohort_db = sqlite3.connect(str(_DATABASE_PATH))
        _cohort_db.row_factory = sqlite3.Row
        _cohort_cols = [r['name'] for r in _cohort_db.execute('PRAGMA table_info(assessments)')]
        _cohort_map = {c.lower(): c for c in _cohort_cols}
        _cohort_id = _cohort_map.get('id') or _cohort_map.get('assessment_id')
        _cohort_aid = state.get('assessment_id')
        if _cohort_id and _cohort_aid is not None:
            _cohort_row = _cohort_db.execute(f'SELECT * FROM assessments WHERE "{_cohort_id}"=?', (int(_cohort_aid),)).fetchone()
            if _cohort_row:
                for _target, _sources in {'school_id': ('school_id',), 'class_level': ('class_level', 'student_class_level'), 'student_class_level': ('student_class_level', 'class_level'), 'section': ('section',)}.items():
                    for _candidate in _sources:
                        _col = _cohort_map.get(_candidate)
                        if _col and _cohort_row[_col] is not None and str(_cohort_row[_col]).strip():
                            state[_target] = _cohort_row[_col]
                            break
    finally:
        try:
            _cohort_db.close()
        except Exception:
            pass
    return state


def _get_state(workflow_id: str) -> dict[str, Any]:
    with _lock:
        state = _states.get(workflow_id)

    if state is None:
        state_file = _STATE_DIRECTORY / f"{workflow_id}.json"
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise HTTPException(
                    status_code=500,
                    detail="Persisted assessment workflow state could not be read.",
                ) from exc

            with _lock:
                _states[workflow_id] = state

    if state is None:
        state = _recover_published_state(workflow_id)
        if state is not None:
            state = _save_state(state)

    if state is None:
        raise HTTPException(status_code=404, detail="Workflow not found.")

    # A workflow may be loaded from memory or a snapshot that lacks DB fields.
    state = _hydrate_published_state(state)
    with _lock:
        _states[workflow_id] = state
    return state


def _save_state(state: dict[str, Any]) -> dict[str, Any]:
    workflow_id = str(state.get("workflow_id") or state.get("request_id") or "")

    if not workflow_id:
        raise HTTPException(status_code=500, detail="Workflow ID is missing.")

    state["workflow_id"] = workflow_id

    with _lock:
        _states[workflow_id] = state
    _STATE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    state_file = _STATE_DIRECTORY / f"{workflow_id}.json"
    try:
        state_file.write_text(
            json.dumps(jsonable_encoder(state), ensure_ascii=True),
            encoding="utf-8",
        )
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail="Assessment workflow state could not be persisted.",
        ) from exc

    return state


def _response(state: dict[str, Any]) -> dict[str, Any]:
    safe = dict(state)
    safe.pop("uploaded_file_path", None)
    return jsonable_encoder(safe)


def _build_state(
    *,
    teacher_request: str,
    teacher_id: str,
    school_id: str,
    topic: str,
    question_count: int,
    marks: int,
    mode: str,
    subject: str = "",
    chapter: str = "",
    class_level: str = "",
    student_class_level: str = "",
    section: str = "",
    classroom_course_id: str = "",
    conversation_id: str = "",
    uploaded_file_path: str = "",
    uploaded_file_name: str = "",
    uploaded_file_type: str = "",
) -> dict[str, Any]:
    request_id = f"tco_{uuid4().hex}"

    preferences = {
        "general_knowledge": ("general_knowledge", ""),
        "teacher_file": ("teacher_file_only", "teacher_file"),
        "classroom": ("classroom_only", "google_classroom"),
        "web_search": ("web_search_only", "web_search"),
    }

    source_preference, knowledge_source = preferences[mode]
    is_source_grounded = mode != "general_knowledge"

    return {
        "request_id": request_id,
        "workflow_id": request_id,
        "conversation_id": conversation_id.strip() or request_id,
        "teacher_id": teacher_id.strip(),
        "school_id": school_id.strip(),
        "teacher_request": teacher_request.strip(),
        "intent": "assessment",
        "language": "english",
        "required_capability": "assessment.create",
        "class_level": class_level.strip(),
        "student_class_level": student_class_level.strip() or class_level.strip(),
        "subject": subject.strip(),
        "chapter": chapter.strip(),
        "topic": topic.strip(),
        "marks": marks,
        "question_count": question_count,
        "section": section.strip(),
        "classroom_course_id": classroom_course_id.strip(),
        "generation_mode": "source_grounded" if is_source_grounded else "llm_generated",
        "source_preference": source_preference,
        "knowledge_source": knowledge_source,
        "requested_source": "",
        "source_url": "",
        "uploaded_file_path": uploaded_file_path,
        "uploaded_file_name": uploaded_file_name,
        "uploaded_file_type": uploaded_file_type,
        "uploaded_source_id": "",
        "web_source_fetched": False,
        "web_source_content_path": "",
        "missing_information": [],
        "source_candidates": [],
        "selected_source": {},
        "source_approved": False,
        "approval_required": False,
        "approval_type": "",
        "approval_status": "not_ready",
        "approved_by": "",
        "approval_comment": "",
        "assessment_review_attempts": 0,
        "assessment_review_status": "not_started",
        "assessment_review_feedback": "",
        "questions": [],
        "answer_key": [],
        "marking_scheme": [],
        "status": "starting",
        "metadata": {
            "api": "tco-assessment-workflow",
            "mode": mode,
        },
    }


def _run_generation(state: dict[str, Any]) -> dict[str, Any]:
    mode = str(state.get("metadata", {}).get("mode", "general_knowledge"))

    try:
        if mode == "general_knowledge":
            result = _get_workflow().generate_and_review(state)
        else:
            # Match the existing Streamlit backup's Work Mode entry point.
            from backend.graph import workflow as master_workflow

            result = master_workflow.invoke(state)

            if result.get("status") == "assessment_ready_for_review":
                # The existing Streamlit backup currently marks this stage
                # as review-bypassed for its delivery test flow.
                result["assessment_review_status"] = "passed"
                result["assessment_review_feedback"] = (
                    "Review bypassed by the existing delivery test flow."
                )
                result["approval_required"] = True
                result["approval_type"] = "assessment"
                result["approval_status"] = "pending"
                result["status"] = "assessment_ready_for_teacher"

        result.setdefault("workflow_id", state["workflow_id"])
        result.setdefault("metadata", state.get("metadata", {}))
        return _save_state(result)

    except HTTPException:
        raise
    except Exception as exc:
        state["status"] = "assessment_generation_failed"
        state["error_code"] = "ASSESSMENT_GENERATION_FAILED"
        state["error_message"] = str(exc)
        _save_state(state)
        raise HTTPException(
            status_code=500,
            detail=f"Assessment generation failed: {exc}",
        ) from exc


@router.post("/generate")
def generate_assessment(request: GenerateAssessmentRequest) -> dict[str, Any]:
    if request.mode == "teacher_file":
        raise HTTPException(
            status_code=400,
            detail="Teacher File mode requires the multipart /generate-with-file endpoint.",
        )

    if request.mode == "classroom" and not request.classroom_course_id.strip():
        raise HTTPException(
            status_code=422,
            detail="classroom_course_id is required for Classroom mode.",
        )

    state = _build_state(
        teacher_request=request.teacher_request,
        teacher_id=request.teacher_id,
        school_id=request.school_id,
        topic=request.topic,
        question_count=request.question_count,
        marks=request.marks,
        mode=request.mode,
        subject=request.subject,
        chapter=request.chapter,
        class_level=request.class_level,
        student_class_level=request.student_class_level,
        section=request.section,
        classroom_course_id=request.classroom_course_id,
        conversation_id=request.conversation_id,
    )

    return _response(_run_generation(state))


@router.post("/generate-with-file")
async def generate_with_file(
    teacher_request: str = Form(...),
    teacher_id: str = Form(...),
    school_id: str = Form(...),
    topic: str = Form(...),
    question_count: int = Form(..., ge=1, le=200),
    marks: int = Form(..., ge=1, le=10000),
    file: UploadFile = File(...),
    subject: str = Form(""),
    chapter: str = Form(""),
    class_level: str = Form(""),
    student_class_level: str = Form(""),
    section: str = Form(""),
    conversation_id: str = Form(""),
) -> dict[str, Any]:
    filename = Path(file.filename or "source").name
    suffix = Path(filename).suffix.lower()

    if suffix not in {".pdf", ".pptx", ".txt", ".md"}:
        raise HTTPException(
            status_code=415,
            detail="Supported teacher source files are PDF, PPTX, TXT and MD.",
        )

    root = Path(__file__).resolve().parents[2]
    upload_dir = root / "data" / "documents" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    request_id = uuid4().hex
    destination = upload_dir / f"{request_id}{suffix}"

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded source file is empty.")
        if len(content) > 25 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Source file exceeds 25 MB.")
        destination.write_bytes(content)
    finally:
        await file.close()

    state = _build_state(
        teacher_request=teacher_request,
        teacher_id=teacher_id,
        school_id=school_id,
        topic=topic,
        question_count=question_count,
        marks=marks,
        mode="teacher_file",
        subject=subject,
        chapter=chapter,
        class_level=class_level,
        student_class_level=student_class_level,
        section=section,
        conversation_id=conversation_id,
        uploaded_file_path=str(destination),
        uploaded_file_name=filename,
        uploaded_file_type=suffix.lstrip("."),
    )

    state["request_id"] = f"tco_{request_id}"
    state["workflow_id"] = state["request_id"]
    state["conversation_id"] = conversation_id.strip() or state["workflow_id"]

    try:
        return _response(_run_generation(state))
    except Exception:
        # Retain the file for diagnostics; it may be useful if ingestion failed.
        raise


@router.get("/{workflow_id}")
def get_assessment_workflow(workflow_id: str) -> dict[str, Any]:
    return _response(_get_state(workflow_id))


@router.post("/{workflow_id}/approve-and-publish")
def approve_and_publish(workflow_id: str) -> dict[str, Any]:
    state = _get_state(workflow_id)

    if state.get("status") != "assessment_ready_for_teacher":
        raise HTTPException(
            status_code=409,
            detail="Assessment is not waiting for teacher approval.",
        )

    if state.get("form_id"):
        raise HTTPException(
            status_code=409,
            detail="A Google Form has already been created for this workflow.",
        )

    workflow = _get_workflow()

    state = workflow.request_teacher_approval(
        state,
        teacher_id=str(state.get("teacher_id", "")),
        approved=True,
    )

    if state.get("status") != "assessment_approved":
        _save_state(state)
        raise HTTPException(
            status_code=409,
            detail=state.get("error_message", "Teacher approval failed."),
        )

    state = workflow.create_and_publish_form(state)

    if state.get("status") != "assessment_form_published":
        _save_state(state)
        raise HTTPException(
            status_code=502,
            detail=state.get("error_message", "Google Form publishing failed."),
        )

    state = workflow.save_assessment(
        state,
        teacher_id=str(state.get("teacher_id", "")),
        school_id=str(state.get("school_id", "")),
    )
    _save_state(state)

    if state.get("status") == "assessment_database_save_failed":
        raise HTTPException(
            status_code=500,
            detail=state.get("error_message", "Assessment database save failed."),
        )

    if state.get("assessment_id") is not None and state.get("form_id"):
        _record_workflow_assessment(
            workflow_id, int(state["assessment_id"])
        )

    return _response(state)


@router.post("/{workflow_id}/regenerate")
def regenerate_assessment(
    workflow_id: str,
    request: RegenerateRequest,
) -> dict[str, Any]:
    state = _get_state(workflow_id)

    if state.get("status") not in {
        "assessment_ready_for_teacher",
        "assessment_generation_failed",
        "assessment_review_failed",
    }:
        raise HTTPException(
            status_code=409,
            detail="This workflow cannot be regenerated in its current state.",
        )

    if state.get("form_id"):
        raise HTTPException(
            status_code=409,
            detail="An assessment with a published form cannot be regenerated here.",
        )

    feedback = request.feedback.strip()
    if feedback:
        state["teacher_request"] = (
            f"{state.get('teacher_request', '')}\n\n"
            f"Teacher regeneration feedback: {feedback}"
        )

    for key in (
        "questions",
        "answer_key",
        "marking_scheme",
        "form_id",
        "responder_url",
        "edit_url",
        "assessment_id",
        "error_code",
        "error_message",
    ):
        state.pop(key, None)

    state["status"] = "starting"
    state["approval_status"] = "not_ready"
    state["approval_required"] = False
    state["assessment_review_status"] = "not_started"

    return _response(_run_generation(state))


@router.post("/{workflow_id}/cancel")
def cancel_assessment(workflow_id: str) -> dict[str, Any]:
    state = _get_state(workflow_id)

    if state.get("form_id") or state.get("assessment_id"):
        raise HTTPException(
            status_code=409,
            detail="This assessment has already been published or saved; cancel is no longer available.",
        )

    state["status"] = "assessment_cancelled"
    state["approval_status"] = "cancelled"
    state["approval_required"] = False
    return _response(_save_state(state))


@router.post("/{workflow_id}/approve-source")
def approve_web_source(
    workflow_id: str,
    request: SourceApprovalRequest,
) -> dict[str, Any]:
    state = _get_state(workflow_id)

    if state.get("metadata", {}).get("mode") != "web_search":
        raise HTTPException(status_code=409, detail="This is not a Web Search workflow.")

    try:
        from backend.services.source_approval import approve_source
        from backend.rag.source_retrieval import retrieve_source

        result = approve_source(
            state,
            selected_url=request.selected_url.strip(),
            teacher_id=str(state.get("teacher_id", "")),
            approval_comment=request.approval_comment.strip()
            or "Teacher approved source for assessment generation.",
        )

        if not result.success:
            raise HTTPException(
                status_code=422,
                detail=result.error_message or "Web source approval failed.",
            )

        state.update(result.data or {})
        state = retrieve_source(state)

        if not state.get("retrieved_context"):
            state["status"] = "waiting_for_teacher"
            state["error_message"] = (
                state.get("clarification_message")
                or "The approved source did not produce usable context."
            )
            return _response(_save_state(state))

        state = _get_workflow().generate_and_review(state)

        if state.get("status") == "assessment_ready_for_review":
            state["assessment_review_status"] = "passed"
            state["assessment_review_feedback"] = (
                "Review bypassed by the existing delivery test flow."
            )
            state["approval_required"] = True
            state["approval_type"] = "assessment"
            state["approval_status"] = "pending"
            state["status"] = "assessment_ready_for_teacher"

        return _response(_save_state(state))

    except HTTPException:
        raise
    except Exception as exc:
        state["status"] = "assessment_generation_failed"
        state["error_message"] = str(exc)
        _save_state(state)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{workflow_id}/send-to-students")
def send_to_students(
    workflow_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = _get_state(workflow_id)

    if state.get("status") not in {
        "assessment_form_published",
        "assessment_created_not_sent",
        "no_responses",
        "student_email_send_failed",
    }:
        raise HTTPException(
            status_code=409,
            detail="Only a published, not-yet-delivered assessment can be sent to students.",
        )
    if int(state.get("student_email_sent") or 0) > 0:
        raise HTTPException(
            status_code=409,
            detail="Assessment invitations have already been sent; duplicate delivery is blocked.",
        )

    if not state.get("form_id") or not state.get("assessment_id"):
        raise HTTPException(
            status_code=409,
            detail="Published form ID or saved assessment ID is missing.",
        )

    delivery_target = payload or {}
    school_id = str(delivery_target.get("school_id") or state.get("school_id") or "").strip()
    class_level = str(delivery_target.get("class_level") or state.get("student_class_level") or state.get("class_level") or "").strip()
    section = str(delivery_target.get("section") or state.get("section") or "").strip()
    state["school_id"] = school_id
    state["student_class_level"] = class_level
    state["class_level"] = class_level
    state["section"] = section

    if not school_id or not class_level or not section:
        raise HTTPException(
            status_code=422,
            detail="school_id, student class level and section are required before delivery.",
        )

    _save_state(state)
    state = _get_workflow().request_student_send(
        state,
        school_id=school_id,
        class_level=class_level,
        section=section,
        send_to_students=True,
    )
    return _response(_save_state(state))


@router.get("/{workflow_id}/recipients")
def preview_student_recipients(workflow_id: str) -> dict[str, Any]:
    state = _get_state(workflow_id)
    if not state.get("form_id") or not state.get("assessment_id"):
        raise HTTPException(
            status_code=409,
            detail="Publish and save the assessment before loading recipients.",
        )

    school_id = str(state.get("school_id", "")).strip()
    class_level = str(
        state.get("student_class_level") or state.get("class_level") or ""
    ).strip()
    section = str(state.get("section", "")).strip()
    if not school_id or not class_level or not section:
        raise HTTPException(
            status_code=422,
            detail=(
                "The saved assessment has no complete school, class and section "
                "target. Update the assessment audience before delivery."
            ),
        )

    try:
        students_result = build_default_registry().get_tool(
            "db.student.list"
        ).execute(
            operation="db.student.list",
            school_id=school_id,
            class_level=class_level,
            section=section,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not load eligible students: {exc}",
        ) from exc

    if not students_result.success:
        raise HTTPException(
            status_code=502,
            detail=students_result.error_message or "Could not load eligible students.",
        )

    students = students_result.data or []
    valid = [
        student for student in students
        if "@" in str(student.get("email") or "").strip()
    ]
    invalid = len(students) - len(valid)
    already_invited = (
        int(state.get("student_email_sent") or 0)
        if state.get("status") == "assessment_sent_to_students"
        else 0
    )

    def masked_email(value: str) -> str:
        local, _, domain = value.partition("@")
        return f"{local[:1]}***@{domain}" if domain else "***"

    preview = [
        {
            "student_id": student.get("id"),
            "name": student.get("name") or "Student",
            "email": masked_email(str(student.get("email")).strip()),
            "eligible": True,
        }
        for student in valid
    ]
    state["recipient_preview"] = preview
    state["eligible_student_count"] = len(students)
    state["valid_email_count"] = len(valid)
    state["invalid_email_count"] = invalid
    state["already_invited_count"] = already_invited
    return _response(_save_state(state))


@router.post("/{workflow_id}/do-not-send")
def do_not_send(workflow_id: str) -> dict[str, Any]:
    state = _get_state(workflow_id)

    if state.get("status") != "assessment_form_published":
        raise HTTPException(
            status_code=409,
            detail="This workflow is not awaiting student-delivery approval.",
        )

    state["status"] = "assessment_created_not_sent"
    return _response(_save_state(state))


@router.post("/{workflow_id}/evaluate")
def evaluate_responses(workflow_id: str) -> dict[str, Any]:
    state = _get_state(workflow_id)

    if state.get("status") not in {
        "assessment_form_published",
        "assessment_sent_to_students",
        "assessment_created_not_sent",
    }:
        raise HTTPException(
            status_code=409,
            detail="The assessment must be published before evaluating responses.",
        )

    form_id = str(state.get("form_id", "") or "").strip()
    assessment_id = state.get("assessment_id")

    if not form_id or assessment_id is None:
        raise HTTPException(
            status_code=409,
            detail="Google Form ID and saved assessment ID are required.",
        )

    try:
        from backend.agents.evaluation_agent import EvaluationAgent
        from backend.services.assessment_result_lifecycle import AssessmentResultLifecycleService
        from backend.services.assessment_result_service import AssessmentResultService
        from backend.services.evaluation_cycle import EvaluationCycleService
        from backend.services.result_email_service import ResultEmailService
        from backend.services.result_store import ResultStore
        from backend.tools.gmail import GmailTool

        result_store = ResultStore()
        result_service = AssessmentResultService(result_store=result_store)
        evaluation_cycle = EvaluationCycleService(
            evaluation_agent=EvaluationAgent(),
            result_service=result_service,
        )
        email_service = ResultEmailService(
            result_store=result_store,
            gmail_tool=GmailTool(),
        )
        lifecycle = AssessmentResultLifecycleService(
            evaluation_cycle=evaluation_cycle,
            result_email_service=email_service,
        )

        results = lifecycle.process_form(
            form_id=form_id,
            assessment_id=int(assessment_id),
            school_id=state.get("school_id") or None,
            class_level=state.get("student_class_level") or None,
            section=state.get("section") or None,
            send_email=False,
        )

        state["evaluation_results"] = results
        if not results:
            state["evaluation_status"] = "no_responses"
            state["status"] = "no_responses"
        else:
            state["evaluation_status"] = "completed"
            state["status"] = "evaluation_completed"
        return _response(_save_state(state))

    except Exception as exc:
        state["evaluation_status"] = "failed"
        state["error_message"] = str(exc)
        _save_state(state)
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {exc}") from exc


@router.post("/{workflow_id}/send-result-emails")
def send_result_emails(workflow_id: str) -> dict[str, Any]:
    state = _get_state(workflow_id)

    if state.get("evaluation_status") != "completed":
        raise HTTPException(
            status_code=409,
            detail="Evaluate and save the student results before sending result emails.",
        )

    assessment_id = state.get("assessment_id")
    if assessment_id is None:
        raise HTTPException(status_code=409, detail="Assessment ID is missing.")

    try:
        from backend.services.assessment_result_service import AssessmentResultService
        from backend.services.result_email_service import ResultEmailService
        from backend.services.result_store import ResultStore
        from backend.tools.gmail import GmailTool

        result_store = ResultStore()
        email_service = ResultEmailService(
            result_store=result_store,
            gmail_tool=GmailTool(),
        )

        summary = email_service.send_pending_results(
            assessment_id=int(assessment_id),
        )

        state["result_email_summary"] = summary
        state["result_email_status"] = str(summary.get("status", "completed"))
        return _response(_save_state(state))

    except Exception as exc:
        state["result_email_status"] = "failed"
        state["error_message"] = str(exc)
        _save_state(state)
        raise HTTPException(
            status_code=500,
            detail=f"Result email delivery failed: {exc}",
        ) from exc
