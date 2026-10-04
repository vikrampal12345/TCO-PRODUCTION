from __future__ import annotations

import re
from typing import Any

from backend.rag.retriever import (
    retrieve_source_context,
)
from backend.services.classroom_discovery import (
    ClassroomDiscoveryError,
    ClassroomMaterialDiscoveryService,
)
from backend.services.classroom_ingestion import (
    ClassroomIngestionError,
    ClassroomIngestionService,
)
from backend.services.file_ingestion import (
    FileIngestionError,
    TeacherFileIngestionService,
)


DEFAULT_TOP_K = 5
DEFAULT_SIMILARITY_THRESHOLD = 0.30


# ============================================================
# TEXT HELPERS
# ============================================================


def _normalize_text(
    value: Any,
) -> str:
    text = str(
        value or ""
    ).lower()

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text,
    )

    return " ".join(
        text.split()
    )


def _query_terms(
    query: str,
) -> set[str]:

    stopwords = {
        "the",
        "a",
        "an",
        "of",
        "for",
        "to",
        "in",
        "on",
        "and",
        "or",
        "with",
        "from",
        "create",
        "make",
        "generate",
        "question",
        "questions",
        "test",
        "assessment",
        "paper",
        "please",
        "using",
        "about",
        "explain",
    }

    normalized = _normalize_text(
        query
    )

    return {
        term
        for term in normalized.split()
        if len(term) >= 2
        and term not in stopwords
    }


# ============================================================
# CLASSROOM ATTACHMENT SCORING
# ============================================================


def _attachment_score(
    attachment: dict[str, Any],
    query: str,
) -> float:

    if attachment.get(
        "supported"
    ) is not True:
        return -1.0

    title = _normalize_text(
        attachment.get(
            "title",
            "",
        )
    )

    query_normalized = _normalize_text(
        query
    )

    terms = _query_terms(
        query
    )

    score = 0.0

    if (
        query_normalized
        and query_normalized in title
    ):
        score += 100.0

    for term in terms:
        if term in title.split():
            score += 10.0

    mode = str(
        attachment.get(
            "mode",
            "",
        )
    ).lower()

    if mode in {
        "download",
        "export",
    }:
        score += 1.0

    return score


def _select_best_attachment(
    discovery_results: list[dict[str, Any]],
    query: str,
) -> tuple[
    dict[str, Any] | None,
    dict[str, Any] | None,
]:

    best_material: (
        dict[str, Any] | None
    ) = None

    best_attachment: (
        dict[str, Any] | None
    ) = None

    best_score = -1.0

    for material in discovery_results:

        for attachment in material.get(
            "attachments",
            [],
        ):

            score = _attachment_score(
                attachment,
                query,
            )

            if score < 0:
                continue

            material_score = float(
                material.get(
                    "relevance_score",
                    0.0,
                )
                or 0.0
            )

            combined_score = (
                material_score
                + score
            )

            if combined_score > best_score:

                best_score = (
                    combined_score
                )

                best_material = (
                    material
                )

                best_attachment = (
                    attachment
                )

    return (
        best_material,
        best_attachment,
    )


# ============================================================
# CLASSROOM COURSE RESOLUTION
# ============================================================


def _resolve_course_id(
    state: dict[str, Any],
    discovery_service: (
        ClassroomMaterialDiscoveryService
    ),
) -> tuple[str | None, str | None]:

    explicit_course_id = str(
        state.get(
            "classroom_course_id",
            state.get(
                "course_id",
                "",
            ),
        )
        or ""
    ).strip()

    if explicit_course_id:
        return (
            explicit_course_id,
            None,
        )

    try:
        courses = (
            discovery_service
            .classroom
            .list_courses()
        )

    except Exception as exc:
        return (
            None,
            f"Could not list Google Classroom courses: {exc}",
        )

    if not courses:
        return (
            None,
            "No active Google Classroom courses were found.",
        )

    active_courses = []

    for course in courses:

        course_state = str(
            course.get(
                "courseState",
                "ACTIVE",
            )
            or "ACTIVE"
        ).upper()

        if course_state in {
            "ARCHIVED",
            "DECLINED",
        }:
            continue

        course_id = str(
            course.get(
                "id",
                "",
            )
            or ""
        ).strip()

        if course_id:
            active_courses.append(
                course
            )

    if len(active_courses) == 1:

        return (
            str(
                active_courses[0].get(
                    "id"
                )
            ).strip(),
            None,
        )

    if len(active_courses) > 1:

        return (
            None,
            (
                "Multiple Google Classroom courses are "
                "available. Please provide "
                "`classroom_course_id` so TCO knows "
                "which course to search."
            ),
        )

    return (
        None,
        "No usable Google Classroom course was found.",
    )


# ============================================================
# RAG QUERY BUILDER
# ============================================================


def _build_rag_query(
    state: dict[str, Any],
) -> str:

    parts = [
        str(
            state.get(
                "subject",
                "",
            )
            or ""
        ).strip(),

        str(
            state.get(
                "chapter",
                "",
            )
            or ""
        ).strip(),

        str(
            state.get(
                "topic",
                "",
            )
            or ""
        ).strip(),
    ]

    requested_source = str(
        state.get(
            "requested_source",
            "",
        )
        or ""
    ).strip()

    if requested_source:
        parts.append(
            requested_source
        )

    teacher_request = str(
        state.get(
            "teacher_request",
            "",
        )
        or ""
    ).strip()

    if teacher_request:
        parts.append(
            teacher_request
        )

    return " ".join(
        part
        for part in parts
        if part
    ).strip()


# ============================================================
# TEACHER FILE RETRIEVAL
# ============================================================


def _retrieve_teacher_file(
    state: dict[str, Any],
) -> dict[str, Any]:

    uploaded_file_path = str(
        state.get(
            "uploaded_file_path",
            "",
        )
        or ""
    ).strip()

    teacher_id = str(
        state.get(
            "teacher_id",
            "",
        )
        or ""
    ).strip()

    school_id = str(
        state.get(
            "school_id",
            "",
        )
        or ""
    ).strip()

    conversation_id = str(
        state.get(
            "conversation_id",
            "",
        )
        or ""
    ).strip()

    topic = str(
        state.get(
            "topic",
            "",
        )
        or ""
    ).strip()

    if not uploaded_file_path:
        return {
            **state,
            "source_available": False,
            "source_status": "missing_uploaded_file",
            "source_approved": False,
            "approval_required": True,
            "approval_type": "source",
            "approval_status": "pending",
            "retrieved_context": "",
            "source_references": [],
            "next_action": "ask_teacher",
            "status": "waiting_for_teacher",
            "clarification_message": (
                "Please upload a valid reference file."
            ),
        }

    if not teacher_id:
        return {
            **state,
            "source_available": False,
            "source_status": "missing_teacher_context",
            "source_approved": False,
            "approval_required": True,
            "approval_type": "source",
            "approval_status": "pending",
            "retrieved_context": "",
            "source_references": [],
            "next_action": "ask_teacher",
            "status": "waiting_for_teacher",
            "clarification_message": (
                "Teacher ID is required to process "
                "the uploaded reference material."
            ),
        }

    if not school_id:
        return {
            **state,
            "source_available": False,
            "source_status": "missing_school_context",
            "source_approved": False,
            "approval_required": True,
            "approval_type": "source",
            "approval_status": "pending",
            "retrieved_context": "",
            "source_references": [],
            "next_action": "ask_teacher",
            "status": "waiting_for_teacher",
            "clarification_message": (
                "School ID is required to process "
                "the uploaded reference material."
            ),
        }

    if not topic:
        return {
            **state,
            "source_available": False,
            "source_status": "missing_topic",
            "source_approved": False,
            "approval_required": True,
            "approval_type": "source",
            "approval_status": "pending",
            "retrieved_context": "",
            "source_references": [],
            "next_action": "ask_teacher",
            "status": "waiting_for_teacher",
            "clarification_message": (
                "Please provide the topic for the "
                "assessment."
            ),
        }

    ingestion_service = (
        TeacherFileIngestionService()
    )

    # ========================================================
    # 1. INGEST TEACHER FILE
    # ========================================================

    try:
        ingestion_result = (
            ingestion_service.ingest(
                uploaded_file_path,
                teacher_id=teacher_id,
                school_id=school_id,
                conversation_id=conversation_id,
            )
        )

    except FileIngestionError as exc:
        return {
            **state,
            "source_available": False,
            "source_status": (
                "teacher_file_ingestion_failed"
            ),
            "source_approved": False,
            "approval_required": True,
            "approval_type": "source",
            "approval_status": "pending",
            "retrieved_context": "",
            "source_references": [],
            "next_action": "ask_teacher",
            "status": "source_ingestion_failed",
            "error_code": (
                "TEACHER_FILE_INGESTION_FAILED"
            ),
            "error_message": str(exc),
            "clarification_message": (
                "I could not process the uploaded "
                "reference material."
            ),
        }

    except Exception as exc:
        return {
            **state,
            "source_available": False,
            "source_status": (
                "teacher_file_ingestion_failed"
            ),
            "source_approved": False,
            "approval_required": True,
            "approval_type": "source",
            "approval_status": "pending",
            "retrieved_context": "",
            "source_references": [],
            "next_action": "ask_teacher",
            "status": "source_ingestion_failed",
            "error_code": (
                "TEACHER_FILE_INGESTION_UNEXPECTED_ERROR"
            ),
            "error_message": str(exc),
            "clarification_message": (
                "An unexpected error occurred while "
                "processing the uploaded reference material."
            ),
        }

    source_id = str(
        ingestion_result.get(
            "source_id",
            "",
        )
        or ""
    ).strip()

    if not source_id:
        return {
            **state,
            "source_available": False,
            "source_status": (
                "missing_teacher_file_source_id"
            ),
            "source_approved": False,
            "approval_required": True,
            "approval_type": "source",
            "approval_status": "pending",
            "retrieved_context": "",
            "source_references": [],
            "next_action": "ask_teacher",
            "status": "source_ingestion_failed",
            "error_code": (
                "TEACHER_FILE_SOURCE_ID_MISSING"
            ),
            "error_message": (
                "Teacher file ingestion succeeded, "
                "but no source_id was returned."
            ),
            "clarification_message": (
                "The uploaded file was processed, "
                "but TCO could not identify its RAG source."
            ),
        }

    file_path = str(
        ingestion_result.get(
            "file_path",
            "",
        )
        or ""
    ).strip()

    if not file_path:
        return {
            **state,
            "source_available": False,
            "source_status": (
                "missing_teacher_file_path"
            ),
            "source_approved": False,
            "approval_required": True,
            "approval_type": "source",
            "approval_status": "pending",
            "retrieved_context": "",
            "source_references": [],
            "next_action": "ask_teacher",
            "status": "source_ingestion_failed",
            "error_code": (
                "TEACHER_FILE_PATH_MISSING"
            ),
            "error_message": (
                "Teacher file ingestion succeeded, "
                "but no file path was returned."
            ),
            "clarification_message": (
                "The uploaded file was processed, "
                "but TCO could not locate the processed file."
            ),
        }

    # ========================================================
    # 2. BUILD RAG QUERY
    # ========================================================

    rag_query = _build_rag_query(
        state
    )

    if not rag_query:
        rag_query = topic

    # ========================================================
    # 3. RETRIEVE CONTEXT
    # ========================================================

    try:
        context = retrieve_source_context(
            query=rag_query,
            source=file_path,
            top_k=DEFAULT_TOP_K,
            similarity_threshold=DEFAULT_SIMILARITY_THRESHOLD,
        )

    except Exception as exc:
        return {
            **state,
            "source_available": False,
            "source_status": (
                "teacher_file_rag_failed"
            ),
            "source_approved": False,
            "approval_required": True,
            "approval_type": "source",
            "approval_status": "pending",
            "uploaded_file_path": file_path,
            "uploaded_file_name": ingestion_result.get(
                "file_name",
                "",
            ),
            "uploaded_file_type": ingestion_result.get(
                "file_type",
                "",
            ),
            "uploaded_source_id": source_id,
            "retrieved_context": "",
            "source_references": [],
            "next_action": "ask_teacher",
            "status": "source_rag_failed",
            "error_code": (
                "TEACHER_FILE_RAG_RETRIEVAL_FAILED"
            ),
            "error_message": str(exc),
            "clarification_message": (
                "The uploaded file was indexed, "
                "but RAG retrieval failed."
            ),
            "knowledge_source": "teacher_file",
            "metadata": {
                **state.get(
                    "metadata",
                    {},
                ),
                "knowledge_source": "teacher_file",
                "ingestion_result": ingestion_result,
            },
        }

    if not context:
        return {
            **state,
            "source_available": False,
            "source_status": (
                "no_relevant_teacher_file_context"
            ),
            "source_approved": False,
            "approval_required": True,
            "approval_type": "source",
            "approval_status": "pending",
            "uploaded_file_path": file_path,
            "uploaded_file_name": ingestion_result.get(
                "file_name",
                "",
            ),
            "uploaded_file_type": ingestion_result.get(
                "file_type",
                "",
            ),
            "uploaded_source_id": source_id,
            "selected_source": {
                "title": ingestion_result.get(
                    "file_name",
                    "",
                ),
                "url": "",
                "source_type": "teacher_file",
                "approved": True,
            },
            "retrieved_context": "",
            "source_references": [],
            "next_action": "ask_teacher",
            "status": "source_not_found",
            "clarification_message": (
                f"I found the uploaded file for "
                f"'{topic}', but could not retrieve "
                "relevant content from it."
            ),
            "knowledge_source": "teacher_file",
            "metadata": {
                **state.get(
                    "metadata",
                    {},
                ),
                "knowledge_source": "teacher_file",
                "ingestion_result": ingestion_result,
            },
        }

    # ========================================================
    # 4. BUILD SOURCE STATE
    # ========================================================

    file_name = str(
        ingestion_result.get(
            "file_name",
            "",
        )
        or ""
    ).strip()

    file_type = str(
        ingestion_result.get(
            "file_type",
            "",
        )
        or ""
    ).strip()

    selected_source = {
        "title": file_name,
        "url": "",
        "source_type": "teacher_file",
        "approved": True,
    }

    return {
        **state,

        "source": source_id,

        "source_available": True,

        "source_status": "source_ready",

        # Teacher explicitly supplied this source.
        "source_approved": True,

        "approval_required": False,

        "approval_type": "source",

        "approval_status": "approved",

        "approved_by": "teacher_uploaded",

        "uploaded_file_path": file_path,

        "uploaded_file_name": file_name,

        "uploaded_file_type": file_type,

        "uploaded_source_id": source_id,

        "knowledge_source": "teacher_file",

        "selected_source": selected_source,

        "retrieved_context": context,

        "source_references": [
            source_id
        ],

        "next_action": "execute_task",

        "status": "source_retrieved",

        "metadata": {
            **state.get(
                "metadata",
                {},
            ),

            "knowledge_source": "teacher_file",

            "uploaded_file_name": file_name,

            "uploaded_file_type": file_type,

            "uploaded_source_id": source_id,

            "ingestion_result": (
                ingestion_result
            ),
        },
    }


# ============================================================
# MAIN SOURCE RETRIEVAL
# ============================================================


def retrieve_source(
    state: dict[str, Any],
) -> dict[str, Any]:
    """
    Work Mode source retrieval.

    Priority currently implemented:

        Teacher uploaded file
            ↓
        Google Classroom
            ↓
        Ask teacher when no source is available

    Teacher-uploaded files are explicitly supplied
    by the teacher and therefore treated as approved.

    This node does not generate assessment content.
    """

    topic = str(
        state.get(
            "topic",
            "",
        )
        or ""
    ).strip()

    if not topic:
        return {
            **state,
            "source_available": False,
            "source_status": "missing_topic",
            "source_approved": False,
            "approval_required": True,
            "approval_type": "source",
            "approval_status": "pending",
            "retrieved_context": "",
            "source_references": [],
            "next_action": "ask_teacher",
            "status": "waiting_for_teacher",
            "clarification_message": (
                "Please provide the exact chapter "
                "name or topic."
            ),
        }

    teacher_id = str(
        state.get(
            "teacher_id",
            "",
        )
        or ""
    ).strip()

    school_id = str(
        state.get(
            "school_id",
            "",
        )
        or ""
    ).strip()

    conversation_id = str(
        state.get(
            "conversation_id",
            "",
        )
        or ""
    ).strip()

    if not teacher_id:
        return {
            **state,
            "source_available": False,
            "source_status": (
                "missing_teacher_context"
            ),
            "source_approved": False,
            "approval_required": True,
            "approval_type": "source",
            "approval_status": "pending",
            "retrieved_context": "",
            "source_references": [],
            "next_action": "ask_teacher",
            "status": "waiting_for_teacher",
            "clarification_message": (
                "Teacher ID is required to use "
                "Classroom knowledge safely."
            ),
        }

    if not school_id:
        return {
            **state,
            "source_available": False,
            "source_status": (
                "missing_school_context"
            ),
            "source_approved": False,
            "approval_required": True,
            "approval_type": "source",
            "approval_status": "pending",
            "retrieved_context": "",
            "source_references": [],
            "next_action": "ask_teacher",
            "status": "waiting_for_teacher",
            "clarification_message": (
                "School ID is required to use "
                "Classroom knowledge safely."
            ),
        }

    # ========================================================
    # 0. TEACHER-UPLOADED FILE
    # ========================================================

    uploaded_file_path = str(
        state.get(
            "uploaded_file_path",
            "",
        )
        or ""
    ).strip()

    if uploaded_file_path:
        return _retrieve_teacher_file(
            state
        )

    # ========================================================
    # CLASSROOM SERVICES
    # ========================================================

    discovery_service = (
        ClassroomMaterialDiscoveryService()
    )

    ingestion_service = (
        ClassroomIngestionService()
    )

    # ========================================================
    # 1. RESOLVE CLASSROOM COURSE
    # ========================================================

    course_id, course_error = (
        _resolve_course_id(
            state,
            discovery_service,
        )
    )

    if course_error:
        return {
            **state,
            "source_available": False,
            "source_status": (
                "classroom_course_unresolved"
            ),
            "source_approved": False,
            "approval_required": True,
            "approval_type": "source",
            "approval_status": "pending",
            "retrieved_context": "",
            "source_references": [],
            "next_action": "ask_teacher",
            "status": "waiting_for_teacher",
            "clarification_message": course_error,
        }

    assert course_id is not None

    # ========================================================
    # 2. CLASSROOM DISCOVERY
    # ========================================================

    discovery_query = _build_rag_query(
        state
    )

    if not discovery_query:
        discovery_query = topic

    try:
        discovery_results = (
            discovery_service.discover(
                course_id=course_id,
                query=discovery_query,
                top_k=DEFAULT_TOP_K,
            )
        )

    except ClassroomDiscoveryError as exc:
        return {
            **state,
            "source_available": False,
            "source_status": (
                "classroom_discovery_failed"
            ),
            "source_approved": False,
            "approval_required": True,
            "approval_type": "source",
            "approval_status": "pending",
            "retrieved_context": "",
            "source_references": [],
            "next_action": "ask_teacher",
            "status": "source_discovery_failed",
            "error_code": (
                "CLASSROOM_DISCOVERY_FAILED"
            ),
            "error_message": str(exc),
            "clarification_message": (
                "I couldn't search Google Classroom "
                "for the requested topic."
            ),
        }

    discovery_results = (
        discovery_results
        or []
    )

    # ========================================================
    # 3. SELECT MATERIAL + ATTACHMENT
    # ========================================================

    selected_material, selected_attachment = (
        _select_best_attachment(
            discovery_results,
            discovery_query,
        )
    )

    if (
        selected_material is None
        or selected_attachment is None
    ):
        return {
            **state,
            "source_available": False,
            "source_status": (
                "no_classroom_source"
            ),
            "source_approved": False,
            "approval_required": True,
            "approval_type": "source",
            "approval_status": "pending",
            "source_candidates": (
                discovery_results
            ),
            "selected_source": {},
            "retrieved_context": "",
            "source_references": [],
            "next_action": "ask_teacher",
            "status": "source_not_found",
            "clarification_message": (
                "I couldn't find relevant supported "
                "material in Google Classroom. "
                "Please provide notes/reference material, "
                "provide a source URL, or explicitly allow "
                "AI-generated content."
            ),
        }

    material_id = str(
        selected_material.get(
            "material_id",
            "",
        )
        or ""
    ).strip()

    drive_file_id = str(
        selected_attachment.get(
            "file_id",
            "",
        )
        or ""
    ).strip()

    attachment_title = str(
        selected_attachment.get(
            "title",
            "",
        )
        or ""
    ).strip()

    if not material_id:
        return {
            **state,
            "source_available": False,
            "source_status": (
                "invalid_classroom_material"
            ),
            "source_approved": False,
            "approval_required": True,
            "approval_type": "source",
            "approval_status": "pending",
            "source_candidates": (
                discovery_results
            ),
            "next_action": "ask_teacher",
            "status": "source_not_found",
            "clarification_message": (
                "The discovered Classroom material "
                "did not contain a valid material ID."
            ),
        }

    # ========================================================
    # 4. CLASSROOM INGESTION
    # ========================================================

    try:
        ingestion_result = (
            ingestion_service.ingest_material(
                course_id=course_id,
                material_id=material_id,
                teacher_id=teacher_id,
                school_id=school_id,
                conversation_id=conversation_id,
                drive_file_id=(
                    drive_file_id or None
                ),
                attachment_title=(
                    attachment_title or None
                ),
            )
        )

    except ClassroomIngestionError as exc:
        return {
            **state,
            "source_available": False,
            "source_status": (
                "classroom_ingestion_failed"
            ),
            "source_approved": False,
            "approval_required": True,
            "approval_type": "source",
            "approval_status": "pending",
            "source_candidates": (
                discovery_results
            ),
            "selected_source": (
                selected_material
            ),
            "retrieved_context": "",
            "source_references": [],
            "next_action": "ask_teacher",
            "status": "source_ingestion_failed",
            "error_code": (
                "CLASSROOM_INGESTION_FAILED"
            ),
            "error_message": str(exc),
            "clarification_message": (
                "I found relevant Classroom material, "
                "but TCO could not ingest it into RAG."
            ),
        }

    source_id = str(
        ingestion_result.get(
            "source_id",
            "",
        )
        or ""
    ).strip()

    if not source_id:
        return {
            **state,
            "source_available": False,
            "source_status": (
                "missing_ingestion_source_id"
            ),
            "source_approved": False,
            "approval_required": True,
            "approval_type": "source",
            "approval_status": "pending",
            "retrieved_context": "",
            "source_references": [],
            "next_action": "ask_teacher",
            "status": "source_ingestion_failed",
            "error_code": (
                "CLASSROOM_SOURCE_ID_MISSING"
            ),
            "clarification_message": (
                "The Classroom material was ingested, "
                "but TCO could not identify its RAG source."
            ),
        }

    # ========================================================
    # 5. CLASSROOM RAG RETRIEVAL
    # ========================================================

    rag_query = _build_rag_query(
        state
    )

    if not rag_query:
        rag_query = topic

    try:
        context = retrieve_source_context(
            query=rag_query,
            source=ingestion_result["file_path"],
            top_k=DEFAULT_TOP_K,
            similarity_threshold=DEFAULT_SIMILARITY_THRESHOLD,
        )

        source_references = [
            source_id
        ]

    except Exception as exc:
        return {
            **state,
            "source_available": False,
            "source_status": (
                "source_rag_failed"
            ),
            "source_approved": False,
            "approval_required": True,
            "approval_type": "source",
            "approval_status": "pending",
            "retrieved_context": "",
            "source_references": [],
            "next_action": "ask_teacher",
            "status": "source_rag_failed",
            "error_code": (
                "CLASSROOM_RAG_RETRIEVAL_FAILED"
            ),
            "error_message": str(exc),
            "clarification_message": (
                "The Classroom material was ingested, "
                "but RAG retrieval failed."
            ),
        }

    if not context:
        return {
            **state,
            "source_available": False,
            "source_status": (
                "no_relevant_classroom_context"
            ),
            "source_approved": False,
            "approval_required": True,
            "approval_type": "source",
            "approval_status": "pending",
            "source_candidates": (
                discovery_results
            ),
            "selected_source": {
                **selected_material,
                "selected_attachment": (
                    selected_attachment
                ),
            },
            "retrieved_context": "",
            "source_references": [],
            "next_action": "ask_teacher",
            "status": "source_not_found",
            "clarification_message": (
                f"I found Classroom material for "
                f"'{topic}', but couldn't retrieve "
                "relevant content from it."
            ),
        }

    # ========================================================
    # 6. BUILD CLASSROOM SOURCE STATE
    # ========================================================

    selected_source = {
        **selected_material,
        "selected_attachment": (
            selected_attachment
        ),
    }

    return {
        **state,

        "classroom_course_id": course_id,

        "classroom_material_id": material_id,

        "classroom_drive_file_id": (
            drive_file_id
        ),

        "classroom_attachment_title": (
            attachment_title
        ),

        "source": source_id,

        "source_available": True,

        "source_status": "source_ready",

        # Google Classroom is an authorized internal source
        # in the current Work Mode flow.
        "source_approved": True,

        "approval_required": False,

        "approval_type": "source",

        "approval_status": "approved",

        "approved_by": "classroom_authorized",

        "source_candidates": (
            discovery_results
        ),

        "selected_source": (
            selected_source
        ),

        "retrieved_context": context,

        "source_references": (
            source_references
        ),

        "next_action": "execute_task",

        "status": "source_retrieved",

        "knowledge_source": (
            "google_classroom"
        ),

        "metadata": {
            **state.get(
                "metadata",
                {},
            ),

            "knowledge_source": (
                "google_classroom"
            ),

            "classroom_course_id": (
                course_id
            ),

            "classroom_material_id": (
                material_id
            ),

            "classroom_drive_file_id": (
                drive_file_id
            ),

            "classroom_attachment_title": (
                attachment_title
            ),

            "ingestion_result": (
                ingestion_result
            ),
        },
    }