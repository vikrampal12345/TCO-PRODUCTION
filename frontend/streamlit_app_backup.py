from __future__ import annotations

import sys

from pathlib import Path

from datetime import datetime

import re

from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent

UPLOAD_ROOT = PROJECT_ROOT / "data" / "documents" / "uploads"

ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".pptx", ".txt", ".md"}

MODE_TEACHER_FILE = "Work Mode — Teacher File + RAG"

MODE_CLASSROOM = "Work Mode — Classroom + RAG"

MODE_WEB = "Work Mode — Web Search + RAG"

MODE_LLM = "AI General Knowledge — Test Mode"

if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from backend.core.bootstrap import build_default_registry

from backend.graph import workflow as master_workflow

from backend.rag.source_retrieval import retrieve_source

from backend.services.source_approval import approve_source
from backend.agents.evaluation_agent import EvaluationAgent
from backend.services.assessment_result_lifecycle import AssessmentResultLifecycleService
from backend.services.assessment_result_service import AssessmentResultService
from backend.services.evaluation_cycle import EvaluationCycleService
from backend.services.result_email_service import ResultEmailService
from backend.services.result_store import ResultStore
from backend.tools.gmail import GmailTool

from backend.workflows.assessment_delivery import (

    AssessmentDeliveryWorkflow,

)

st.set_page_config(

    page_title="TCO | Teacher Co-Worker",

    page_icon="🎓",

    layout="wide",

    initial_sidebar_state="expanded",

)

# =========================================================

# PAGE STYLE

# =========================================================

st.markdown(

    """

    <style>

        .block-container {

            padding-top: 1.5rem;

            padding-bottom: 2rem;

        }

        .tco-title {

            font-size: 2.2rem;

            font-weight: 750;

            margin-bottom: 0.15rem;

        }

        .tco-subtitle {

            color: #6b7280;

            font-size: 1rem;

            margin-bottom: 1.2rem;

        }

        .step-card {

            border: 1px solid rgba(128,128,128,0.25);

            border-radius: 12px;

            padding: 0.85rem 1rem;

            margin-bottom: 0.6rem;

        }

        .step-title {

            font-weight: 700;

            margin-bottom: 0.2rem;

        }

        .step-muted {

            color: #6b7280;

            font-size: 0.9rem;

        }

        .question-card {

            border: 1px solid rgba(128,128,128,0.22);

            border-radius: 12px;

            padding: 0.9rem 1rem;

            margin-bottom: 0.75rem;

        }

        .status-pill {

            display: inline-block;

            border-radius: 999px;

            padding: 0.25rem 0.65rem;

            font-size: 0.8rem;

            font-weight: 650;

        }

    </style>

    """,

    unsafe_allow_html=True,

)

# =========================================================

# SESSION STATE

# =========================================================

DEFAULT_STATE: dict[str, Any] = {

    "status": "idle",

    "teacher_request": "",

    "teacher_id": "",

    "school_id": "",

    "conversation_id": "",

    "classroom_course_id": "",

    "class_level": "",

    "student_class_level": "",

    "subject": "",

    "chapter": "",

    "topic": "",

    "marks": 0,

    "question_count": 0,

    "generation_mode": "source_grounded",

    "source_preference": "classroom_first",

    "requested_source": "",

    "source_url": "",

    "uploaded_file_path": "",

    "uploaded_file_name": "",

    "uploaded_file_type": "",

    "uploaded_source_id": "",

    "web_source_fetched": False,

    "web_source_content_path": "",

    "knowledge_source": "",

    "section": "",

}

if "workflow_state" not in st.session_state:

    st.session_state.workflow_state = DEFAULT_STATE.copy()

if "logs" not in st.session_state:

    st.session_state.logs = []

if "registry" not in st.session_state:

    st.session_state.registry = None

if "workflow" not in st.session_state:

    st.session_state.workflow = None

if "evaluation_results" not in st.session_state:

    st.session_state.evaluation_results = []

if "result_email_summary" not in st.session_state:

    st.session_state.result_email_summary = None

# =========================================================

# HELPERS

# =========================================================

def now_label() -> str:

    return datetime.now().strftime("%H:%M:%S")

def add_log(message: str) -> None:

    st.session_state.logs.append(

        {

            "time": now_label(),

            "message": message,

        }

    )

def get_workflow() -> AssessmentDeliveryWorkflow:

    if st.session_state.registry is None:

        st.session_state.registry = build_default_registry()

        add_log("Registry built successfully.")

    if st.session_state.workflow is None:

        st.session_state.workflow = AssessmentDeliveryWorkflow(

            st.session_state.registry,

            max_review_attempts=3,

        )

        add_log("Assessment delivery workflow initialized.")

    return st.session_state.workflow

def reset_workflow() -> None:

    st.session_state.workflow_state = DEFAULT_STATE.copy()

    st.session_state.logs = []
    st.session_state.evaluation_results = []
    st.session_state.result_email_summary = None

    if "web_source_choice" in st.session_state:

        del st.session_state.web_source_choice

    add_log("Workflow reset. Ready for a new assessment.")

def status_label(status: str) -> str:

    labels = {

        "idle": "Ready",

        "assessment_generation_failed": "Generation failed",

        "waiting_for_teacher": "Waiting for teacher/source input",

        "assessment_ready_for_review": "Assessment ready for review",

        "assessment_ready_for_teacher": "Waiting for teacher approval",

        "assessment_approved": "Teacher approved",

        "assessment_form_published": "Google Form published",

        "assessment_database_save_failed": "Database save failed",

        "assessment_created_not_sent": "Created, not sent",

        "student_email_lookup_failed": "Student lookup failed",

        "no_student_recipients": "No students found",

        "student_email_send_failed": "Email sending failed",

        "assessment_sent_to_students": "Sent to students",

        "assessment_rejected_by_teacher": "Rejected by teacher",

        "teacher_approval_failed": "Approval failed",

    }

    return labels.get(status, status.replace("_", " ").title())

def status_type(status: str) -> str:

    if status in {

        "assessment_sent_to_students",

        "assessment_form_published",

        "assessment_approved",

    }:

        return "success"

    if status in {

        "assessment_generation_failed",

        "assessment_database_save_failed",

        "student_email_lookup_failed",

        "no_student_recipients",

        "student_email_send_failed",

        "assessment_rejected_by_teacher",

        "teacher_approval_failed",

    }:

        return "error"

    return "info"

def show_status() -> None:

    state = st.session_state.workflow_state

    current_status = state.get("status", "idle")

    st.caption(

        f"Current workflow status: **{status_label(current_status)}**"

    )

    steps = [

        ("1", "Teacher Input", "input"),

        ("2", "AI Generation", "generated"),

        ("3", "Teacher Approval", "approved"),

        ("4", "Google Form", "form"),

        ("5", "Database", "database"),

        ("6", "Student Delivery", "sent"),

    ]

    status_order = {

        "idle": 0,

        "assessment_ready_for_teacher": 2,

        "assessment_approved": 3,

        "assessment_form_published": 4,

        "assessment_created_not_sent": 5,

        "assessment_sent_to_students": 6,

    }

    progress_step = status_order.get(current_status, 1)

    cols = st.columns(len(steps))

    for index, (number, title, key) in enumerate(steps):

        with cols[index]:

            if index + 1 <= progress_step:

                st.success(f"{number}. {title}")

            else:

                st.info(f"{number}. {title}")

def show_logs() -> None:

    with st.expander("Live process log", expanded=True):

        if not st.session_state.logs:

            st.caption("No process activity yet.")

            return

        for item in reversed(st.session_state.logs):

            st.write(

                f"**[{item['time']}]** {item['message']}"

            )

def display_questions(state: dict[str, Any]) -> None:

    questions = state.get("questions", [])

    if not questions:

        st.warning("No questions were returned by the Assessment Agent.")

        return

    st.subheader("Generated Assessment")

    cols = st.columns(3)

    cols[0].metric("Questions", len(questions))

    cols[1].metric("Total Marks", state.get("marks", 0))

    cols[2].metric("Topic", state.get("topic", ""))

    for index, question in enumerate(questions, start=1):

        question_text = str(

            question.get("question", "")

        ).replace("\\\n", "\n")

        st.markdown(

            f"<div class='question-card'><strong>Q{index}.</strong> "

            f"{question_text}</div>",

            unsafe_allow_html=True,

        )

        options = question.get("options", [])

        for option_number, option in enumerate(

            options,

            start=1,

        ):

            st.write(

                f"**{option_number}.** {option}"

            )

        with st.expander(

            f"Teacher view â€” answer for Q{index}",

            expanded=False,

        ):

            st.write(

                f"Correct option: **{question.get('correct_option', 'N/A')}**"

            )

def show_error(state: dict[str, Any]) -> None:

    error = state.get("error_message")

    if error:

        st.error(error)

def save_teacher_upload(uploaded_file: Any, conversation_id: str) -> dict[str, str]:

    """Persist a Streamlit UploadedFile so backend RAG can ingest it."""

    if uploaded_file is None:

        return {}

    original_name = Path(str(uploaded_file.name)).name

    suffix = Path(original_name).suffix.lower()

    if suffix not in ALLOWED_UPLOAD_EXTENSIONS:

        raise ValueError("Unsupported file type. Upload PDF, PPTX, TXT, or MD.")

    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", original_name).strip("._")

    if not safe_name:

        raise ValueError("The uploaded file name is invalid.")

    upload_dir = UPLOAD_ROOT / conversation_id

    upload_dir.mkdir(parents=True, exist_ok=True)

    target_path = upload_dir / safe_name

    target_path.write_bytes(uploaded_file.getbuffer())

    return {

        "uploaded_file_path": str(target_path),

        "uploaded_file_name": original_name,

        "uploaded_file_type": suffix.lstrip("."),

    }

def build_state_from_form(

    teacher_id: str,

    school_id: str,

    teacher_request: str,

    class_level: str,

    subject: str,

    chapter: str,

    topic: str,

    marks: int,

    question_count: int,

    section: str,

    student_class_level: str,

    *,

    mode: str,

    classroom_course_id: str = "",

    uploaded_file_path: str = "",

    uploaded_file_name: str = "",

    uploaded_file_type: str = "",

) -> dict[str, Any]:

    request_id = (

        f"streamlit_"

        f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

    )

    is_work_mode = mode in {

        MODE_TEACHER_FILE,

        MODE_CLASSROOM,

        MODE_WEB,

    }

    if mode == MODE_TEACHER_FILE:

        source_preference = "teacher_file_only"

        knowledge_source = "teacher_file"

    elif mode == MODE_CLASSROOM:

        source_preference = "classroom_only"

        knowledge_source = "google_classroom"

    elif mode == MODE_WEB:

        source_preference = "web_search_only"

        knowledge_source = "web_search"

    else:

        source_preference = "general_knowledge"

        knowledge_source = ""

    return {

        "request_id": request_id,

        "conversation_id": request_id,

        "teacher_id": teacher_id,

        "school_id": school_id,

        "classroom_course_id": classroom_course_id if mode == MODE_CLASSROOM else "",

        "teacher_request": teacher_request,

        "intent": "assessment",

        "language": "english",

        "required_capability": "assessment.create",

        "class_level": class_level,

        "student_class_level": student_class_level,

        "subject": subject,

        "chapter": chapter,

        "topic": topic,

        "marks": marks,

        "question_count": question_count,

        "generation_mode": "source_grounded" if is_work_mode else "llm_generated",

        "requested_source": "",

        "source_preference": source_preference,

        "source_url": "",

        "uploaded_file_path": uploaded_file_path,

        "uploaded_file_name": uploaded_file_name,

        "uploaded_file_type": uploaded_file_type,

        "uploaded_source_id": "",

        "web_source_fetched": False,

        "web_source_content_path": "",

        "knowledge_source": knowledge_source,

        "section": section,

        "missing_information": [],

        "source_candidates": [],

        "selected_source": {},

        "source_approved": False,

        "approval_required": False,

        "approval_type": "",

        "approval_status": "not_ready",

        "approved_by": "",

        "approval_comment": "",

        "status": "starting",

    }

# =========================================================
# RESULT / EVALUATION SERVICES
# =========================================================

def get_result_lifecycle_services():
    result_store = ResultStore()
    result_service = AssessmentResultService(
        result_store=result_store,
    )
    evaluation_cycle = EvaluationCycleService(
        evaluation_agent=EvaluationAgent(),
        result_service=result_service,
    )
    gmail_tool = GmailTool()
    result_email_service = ResultEmailService(
        result_store=result_store,
        gmail_tool=gmail_tool,
    )
    lifecycle_service = AssessmentResultLifecycleService(
        evaluation_cycle=evaluation_cycle,
        result_email_service=result_email_service,
    )
    return result_store, lifecycle_service, result_email_service


def evaluate_current_assessment():
    state = st.session_state.workflow_state
    form_id = str(state.get("form_id", "") or "").strip()
    assessment_id = state.get("assessment_id")
    if not form_id:
        raise ValueError("Google Form ID is missing.")
    if assessment_id is None:
        raise ValueError("Assessment ID is missing.")
    _, lifecycle_service, _ = get_result_lifecycle_services()
    results = lifecycle_service.process_form(
        form_id=form_id,
        assessment_id=int(assessment_id),
        school_id=state.get("school_id") or None,
        class_level=state.get("student_class_level") or None,
        section=state.get("section") or None,
        send_email=False,
    )
    st.session_state.evaluation_results = results
    st.session_state.result_email_summary = None


def show_evaluation_dashboard(state: dict[str, Any]) -> None:
    assessment_id = state.get("assessment_id")
    form_id = str(state.get("form_id", "") or "").strip()
    if not assessment_id or not form_id:
        return

    st.divider()
    st.subheader("Evaluation & Results")
    st.caption(
        "Evaluate and save results first. Result emails are sent only after teacher approval."
    )

    if st.button(
        "Evaluate Student Responses",
        type="primary",
        use_container_width=True,
        key="evaluate_student_responses",
    ):
        add_log("Master Agent reached the evaluation stage.")
        add_log("Evaluation Agent is processing Google Form responses.")
        with st.spinner("Evaluating responses and saving results..."):
            try:
                evaluate_current_assessment()
                add_log(
                    f"Evaluation completed for assessment {assessment_id}."
                )
            except Exception as exc:
                st.error(f"Evaluation failed: {exc}")
                add_log(f"Evaluation failed: {exc}")

    results = st.session_state.evaluation_results
    if not results:
        st.info(
            "No evaluated responses loaded yet. Students must submit the Google Form first."
        )
        return

    rows = []
    review_count = 0
    identity_required_count = 0
    identity_required_messages = []
    for item in results:
        if item.get("status") == "identity_required":
            identity_required_count += 1
            identity_required_messages.append(
                item.get(
                    "message",
                    "Student identity is missing. Ask the student to resubmit the form.",
                )
            )
            continue
        if item.get("status") == "review_required":
            review_count += 1
            continue
        evaluation = item.get("evaluation_result") or item.get("evaluation") or {}
        saved = item.get("saved_result") or {}
        rows.append({
            "Result ID": saved.get("result_id"),
            "Student": saved.get("student_name") or evaluation.get("student_name") or "Unknown",
            "Email": saved.get("student_email") or "",
            "Marks": f"{evaluation.get('obtained_marks', saved.get('obtained_marks', 0))} / {evaluation.get('total_marks', saved.get('total_marks', 0))}",
            "Percentage": evaluation.get("percentage", saved.get("percentage", 0)),
            "Correct": evaluation.get("correct_answers", saved.get("correct_answers", 0)),
            "Wrong": evaluation.get("wrong_answers", saved.get("wrong_answers", 0)),
            "Unanswered": evaluation.get("unanswered", saved.get("unanswered", 0)),
            "Result Email": saved.get("result_email_status", "not_sent"),
        })

    metrics = st.columns(4)
    metrics[0].metric("Responses", len(results))
    metrics[1].metric("Saved Results", len(rows))
    metrics[2].metric("Review Required", review_count + identity_required_count)
    metrics[3].metric(
        "Average %",
        round(sum(float(r["Percentage"] or 0) for r in rows) / len(rows), 2) if rows else 0,
    )

    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Result Email")
        st.warning(
            "The next action sends real Gmail messages to saved results whose email status is not_sent."
        )
        if st.button(
            "Send Result Emails",
            type="primary",
            use_container_width=True,
            key="send_result_emails",
        ):
            add_log("Teacher approved result-email delivery.")
            with st.spinner("Sending result emails through Gmail..."):
                try:
                    _, _, email_service = get_result_lifecycle_services()
                    summary = email_service.send_pending_results(
                        assessment_id=int(assessment_id),
                    )
                    st.session_state.result_email_summary = summary
                    add_log(
                        f"Result email delivery: {summary.get('sent', 0)} sent, "
                        f"{summary.get('failed', 0)} failed, "
                        f"{summary.get('skipped', 0)} skipped."
                    )
                except Exception as exc:
                    st.session_state.result_email_summary = {
                        "status": "failed",
                        "error": str(exc),
                    }
                    add_log(f"Result email delivery failed: {exc}")

    if identity_required_count:
        st.warning(
            f"{identity_required_count} response(s) are missing student identity."
        )
        for message in dict.fromkeys(identity_required_messages):
            st.info(message)

    if review_count:
        st.warning(f"{review_count} response(s) require review and were not finalized.")

    summary = st.session_state.result_email_summary
    if summary:
        st.divider()
        st.subheader("Result Email Status")
        if summary.get("status") == "failed":
            st.error(summary.get("error", "Result email delivery failed."))
        else:
            cols = st.columns(4)
            cols[0].metric("Processed", summary.get("total", 0))
            cols[1].metric("Sent", summary.get("sent", 0))
            cols[2].metric("Failed", summary.get("failed", 0))
            cols[3].metric("Skipped", summary.get("skipped", 0))
            if summary.get("results"):
                st.dataframe(
                    [
                        {
                            "Result ID": x.get("result_id"),
                            "Recipient": x.get("recipient"),
                            "Status": x.get("status"),
                            "Error": x.get("error", ""),
                        }
                        for x in summary["results"]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )


# SIDEBAR

# =========================================================

with st.sidebar:

    st.header("TCO Teacher Setup")

    teacher_id = st.text_input(

        "Teacher ID",

        value="teacher-demo",

        help="Prototype teacher identifier.",

    )

    school_id = st.text_input(

        "School ID",

        value="TCO_TEST",

        help="Used for student/database filtering.",

    )

    st.divider()

    st.subheader("Assessment")

    mode = st.selectbox(

        "TCO Mode",

        [

            MODE_TEACHER_FILE,

            MODE_CLASSROOM,

            MODE_WEB,

            MODE_LLM,

        ],

        key="tco_mode",

        help=(

            "Teacher File uses only the uploaded source. "

            "Classroom uses only Google Classroom. "

            "Web Search finds sources on the web and waits for teacher approval before RAG. "

            "Test Mode allows general AI knowledge."

        ),

    )

    if mode == MODE_CLASSROOM:

        classroom_course_id = st.text_input(

            "Google Classroom Course ID",

            value="871538502094",

            help=(

                "Course ID used by the connected Google Classroom account."

            ),

        )

    else:

        classroom_course_id = ""

    if mode == MODE_TEACHER_FILE:

        uploaded_file = st.file_uploader(

            "Teacher Source File (required)",

            type=["pdf", "pptx", "txt", "md"],

            key="teacher_source_file",

            help=(

                "This mode uses only this uploaded file. It will be ingested, "

                "retrieved with RAG, and the retrieved context will be passed "

                "to the Assessment Agent."

            ),

        )

        if uploaded_file is not None:

            st.success(f"Selected: {uploaded_file.name}")

            st.caption(

                "Teacher File mode does not call Google Classroom."

            )

    else:

        uploaded_file = None

        if mode == MODE_CLASSROOM:

            st.caption(

                "Classroom mode does not use an uploaded teacher file."

            )

        elif mode == MODE_WEB:

            st.caption(

                "Web Search mode does not use Classroom or a teacher upload."

            )

    class_level = st.text_input(

        "Assessment Class / Year",

        value="BTech 1st Year",

        help="Class/level used to generate the assessment content.",

    )

    student_class_level = st.text_input(

        "Student Target Class / Year",

        value="TCO Test Class",

        help="Must match the students' class_level stored in SQLite for delivery.",

    )

    section = st.text_input(

        "Student Section",

        value="TEST",

        help="Must match the students' section stored in SQLite for delivery.",

    )

    subject = st.text_input(

        "Subject",

        value="Computer Organization",

    )

    chapter = st.text_input(

        "Chapter",

        value="Unit 2",

    )

    topic = st.text_input(

        "Topic",

        value="Booth Algorithm",

    )

    question_count = st.number_input(

        "Number of Questions",

        min_value=1,

        max_value=50,

        value=5,

        step=1,

    )

    marks = st.number_input(

        "Total Marks",

        min_value=1,

        max_value=100,

        value=20,

        step=1,

    )

    if mode == MODE_TEACHER_FILE:

        st.caption(

            "Teacher File Mode: Upload → Ingest → RAG Retrieval → Assessment Agent."

        )

    elif mode == MODE_CLASSROOM:

        st.caption(

            "Classroom Mode: Google Classroom → Ingest → RAG Retrieval → Assessment Agent."

        )

    elif mode == MODE_WEB:

        st.caption(

            "Web Search Mode: Search → Teacher Approval → Fetch → RAG Retrieval → Assessment Agent."

        )

    else:

        st.caption(

            "AI general-knowledge test mode. No source retrieval is performed."

        )

    st.divider()

    if st.button(

        "Reset Workflow",

        use_container_width=True,

    ):

        reset_workflow()

        st.rerun()

# =========================================================

# HEADER

# =========================================================

st.markdown(

    "<div class='tco-title'>TCO â€” Teacher Co-Worker</div>",

    unsafe_allow_html=True,

)

st.markdown(

    "<div class='tco-subtitle'>Create an assessment, approve it, publish it, save it, and deliver it to students â€” while watching every workflow step.</div>",

    unsafe_allow_html=True,

)

show_status()

# =========================================================

# MAIN TABS

# =========================================================

input_tab, process_tab, result_tab = st.tabs(

    [

        "Teacher Input",

        "Process Monitor",

        "Result",

    ]

)

# =========================================================

# TEACHER INPUT TAB

# =========================================================

with input_tab:

    st.subheader("What should TCO do?")

    teacher_request = st.text_area(

        "Teacher request",

        value=(

            "Create a 5-question, 20 marks assessment on "

            "Booth Algorithm for Computer Organization Unit 2."

        ),

        height=120,

        help="This request is passed to the Assessment Agent along with the structured fields.",

    )

    st.info(

        "TCO will generate the assessment first. You will see the complete generated paper before anything is published."

    )

    generate = st.button(

        "Generate Assessment",

        type="primary",

        use_container_width=True,

    )

    if generate:

        if not teacher_id.strip():

            st.error("Teacher ID is required.")

            st.stop()

        if not school_id.strip():

            st.error("School ID is required.")

            st.stop()

        if not subject.strip():

            st.error("Subject is required.")

            st.stop()

        if not topic.strip():

            st.error("Topic is required.")

            st.stop()

        if not student_class_level.strip():

            st.error("Student target class / year is required for delivery.")

            st.stop()

        if not section.strip():

            st.error("Student section is required for delivery.")

            st.stop()

        if mode == MODE_TEACHER_FILE and uploaded_file is None:

            st.error(

                "Teacher File Mode requires a PDF, PPTX, TXT, or MD source file."

            )

            st.stop()

        if mode == MODE_CLASSROOM and not classroom_course_id.strip():

            st.error(

                "Google Classroom Course ID is required in Classroom Mode."

            )

            st.stop()

        state = build_state_from_form(

            teacher_id=teacher_id.strip(),

            school_id=school_id.strip(),

            teacher_request=teacher_request.strip(),

            class_level=class_level.strip(),

            subject=subject.strip(),

            chapter=chapter.strip(),

            topic=topic.strip(),

            marks=int(marks),

            question_count=int(question_count),

            section=section.strip(),

            student_class_level=student_class_level.strip(),

            mode=mode,

            classroom_course_id=(

                classroom_course_id.strip()

                if mode == MODE_CLASSROOM

                else ""

            ),

            uploaded_file_path="",

            uploaded_file_name=(

                str(uploaded_file.name)

                if uploaded_file is not None

                else ""

            ),

            uploaded_file_type=(

                Path(str(uploaded_file.name)).suffix.lower().lstrip(".")

                if uploaded_file is not None

                else ""

            ),

        )

        if uploaded_file is not None:

            try:

                state.update(

                    save_teacher_upload(

                        uploaded_file,

                        conversation_id=state["conversation_id"],

                    )

                )

                state["knowledge_source"] = "teacher_file"

                state["source_preference"] = "teacher_file_only"

            except Exception as exc:

                state["status"] = "assessment_generation_failed"

                state["error_message"] = f"Could not save uploaded source file: {exc}"

                st.session_state.workflow_state = state

                st.error(state["error_message"])

                st.stop()

        st.session_state.workflow_state = state

        st.session_state.logs = []

        add_log("Teacher submitted a new assessment request.")

        add_log(

            f"Request: {teacher_request.strip()}"

        )

        add_log("Routing task to capability: assessment.create")

        with st.spinner("TCO is processing the assessment request..."):

            try:

                if mode in {MODE_TEACHER_FILE, MODE_CLASSROOM, MODE_WEB}:

                    add_log(

                        "Work Mode enabled: invoking Master Agent."

                    )

                    if mode == MODE_TEACHER_FILE:

                        add_log(

                            "Teacher File Mode: Classroom search is disabled."

                        )

                        add_log(

                            f"Reading uploaded source: {state.get('uploaded_file_name', '')}"

                        )

                        add_log(

                            "Uploaded file will be ingested and retrieved through the common RAG pipeline."

                        )

                    elif mode == MODE_CLASSROOM:

                        add_log(

                            "Classroom Mode: Master Agent will use Google Classroom only."

                        )

                    elif mode == MODE_WEB:

                        add_log(

                            "Web Search Mode: Classroom and teacher-file retrieval are disabled."

                        )

                        add_log(

                            "Web source candidates require teacher approval before fetching."

                        )

                    state = master_workflow.invoke(state)

                    if state.get("knowledge_source") == "teacher_file":

                        add_log("Teacher file was ingested and relevant context was retrieved.")

                        add_log("Retrieved context is being passed to the Assessment Agent as generation context.")

                    elif state.get("knowledge_source") == "google_classroom":

                        add_log("Google Classroom material was retrieved through RAG.")

                    elif state.get("knowledge_source") == "web_search":

                        if state.get("source_candidates") and not state.get("source_approved"):

                            add_log(

                                f"Found {len(state.get('source_candidates', []))} web source candidates. Waiting for teacher approval."

                            )

                    if state.get("status") == (

                        "assessment_ready_for_review"

                    ):

                        state["assessment_review_status"] = "passed"

                        state["assessment_review_feedback"] = (

                            "Review bypassed for end-to-end workflow test."

                        )

                        state["status"] = (

                            "assessment_ready_for_teacher"

                        )

                        add_log(

                            "Master Agent completed source-grounded routing."

                        )

                        if state.get("knowledge_source") == "teacher_file":

                            add_log(

                                "Uploaded file was fetched, ingested, retrieved, and supplied to the Assessment Agent."

                            )

                        elif state.get("knowledge_source") == "google_classroom":

                            add_log(

                                "Google Classroom material was found and retrieved through RAG."

                            )

                        elif state.get("knowledge_source") == "web_search":

                            add_log(

                                "Approved web source was extracted, indexed, and retrieved through RAG."

                            )

                        add_log(

                            f"Source approved: "

                            f"{state.get('source_approved')}"

                        )

                        add_log(

                            "Assessment Agent generated the assessment."

                        )

                    elif state.get("status") == "waiting_for_teacher":

                        clarification = state.get(

                            "clarification_message"

                        )

                        if (

                            clarification

                            and not state.get("error_message")

                            and not (

                                state.get("knowledge_source") == "web_search"

                                and state.get("source_candidates")

                            )

                        ):

                            state["error_message"] = clarification

                        add_log(

                            "Work Mode is waiting for teacher/source input."

                        )

                    else:

                        add_log(

                            "Work Mode did not reach assessment generation."

                        )

                else:

                    add_log(

                        "AI general-knowledge test mode enabled."

                    )

                    add_log(

                        "Calling local LLM through Assessment Agent..."

                    )

                    workflow = get_workflow()

                    state = workflow.generate_and_review(state)

                    add_log(

                        "Assessment Agent finished generation."

                    )

                    add_log(

                        "Review Agent is bypassed for this workflow test; "

                        "LLM output is accepted as-is."

                    )

            except Exception as exc:

                state["status"] = "assessment_generation_failed"

                state["error_message"] = str(exc)

                add_log(

                    f"Assessment generation failed: {exc}"

                )

            else:

                if state.get("status") == (

                    "assessment_ready_for_teacher"

                ):

                    add_log(

                        "Assessment is waiting for teacher approval."

                    )

        st.session_state.workflow_state = state

        st.rerun()

    state = st.session_state.workflow_state

    # =====================================================

    # =====================================================
    # WEB SOURCE APPROVAL
    # =====================================================

    if state.get("knowledge_source") == "web_search":

        # -------------------------------------------------
        # CASE 1: Source is already approved.
        # Keep it visible after reruns so a fetch/RAG
        # failure does not look like a UI reset.
        # -------------------------------------------------
        if state.get("source_approved"):

            st.divider()
            st.subheader("Approved Web Source")

            selected_source = state.get(
                "selected_source",
                {},
            ) or {}

            source_title = str(
                selected_source.get(
                    "title",
                    "Approved web source",
                )
                or "Approved web source"
            ).strip()

            source_url = str(
                selected_source.get(
                    "url",
                    "",
                )
                or state.get("source_url", "")
                or ""
            ).strip()

            source_status = str(
                state.get("source_status", "")
                or ""
            ).strip()

            retrieved_context = str(
                state.get("retrieved_context", "")
                or ""
            )

            st.success(
                "Teacher-approved web source is active."
            )

            st.write(
                f"**Source:** {source_title}"
            )

            if source_url:
                st.write(
                    f"**URL:** [{source_url}]({source_url})"
                )

            st.write(
                f"**Source status:** "
                f"`{source_status or 'approved'}`"
            )

            st.write(
                f"**RAG context:** "
                f"{len(retrieved_context)} characters"
            )

            if retrieved_context:
                st.success(
                    "Web source content was fetched and relevant RAG context is ready."
                )

            if state.get("error_message"):
                st.error(
                    str(state.get("error_message"))
                )

            # Approved source is retained even if RAG failed.
            # Allow retry without asking the teacher to search again.
            if not retrieved_context:

                retry_web_rag = st.button(
                    "Retry Fetch & RAG",
                    type="primary",
                    use_container_width=True,
                    key="retry_web_rag",
                )

                if retry_web_rag:

                    add_log(
                        "Retrying the teacher-approved web source."
                    )

                    with st.spinner(
                        "Fetching approved source and retrieving RAG context..."
                    ):
                        try:

                            state = retrieve_source(state)

                            if state.get("retrieved_context"):

                                add_log(
                                    "Approved web source fetched and RAG context is ready."
                                )

                                workflow = get_workflow()

                                with st.spinner(
                                    "Assessment Agent is generating the web-grounded assessment..."
                                ):
                                    state = (
                                        workflow.generate_and_review(
                                            state
                                        )
                                    )

                                if state.get("status") == (
                                    "assessment_ready_for_review"
                                ):
                                    state[
                                        "assessment_review_status"
                                    ] = "passed"

                                    state[
                                        "assessment_review_feedback"
                                    ] = (
                                        "Review bypassed for "
                                        "end-to-end workflow test."
                                    )

                                    state["status"] = (
                                        "assessment_ready_for_teacher"
                                    )

                                    add_log(
                                        "Assessment Agent generated the web-grounded assessment."
                                    )

                            else:

                                clarification = str(
                                    state.get(
                                        "clarification_message",
                                        "",
                                    )
                                    or ""
                                )

                                if clarification:
                                    state["error_message"] = (
                                        clarification
                                    )

                                add_log(
                                    "Retry completed, but no relevant RAG context was retrieved."
                                )

                        except Exception as exc:

                            state["source_approved"] = True
                            state["approval_status"] = "approved"
                            state[
                                "status"
                            ] = "assessment_generation_failed"
                            state[
                                "error_message"
                            ] = str(exc)

                            add_log(
                                f"Web source retry failed: {exc}"
                            )

                    st.session_state.workflow_state = state
                    st.rerun()

        # -------------------------------------------------
        # CASE 2: Search candidates are waiting for approval.
        # -------------------------------------------------
        elif state.get("source_candidates"):

            st.divider()
            st.subheader("Choose a Web Source")

            st.info(
                "TCO found these web sources. Review the source and approve one before TCO fetches it and uses it for assessment generation."
            )

            candidates = [
                dict(candidate)
                for candidate in state.get(
                    "source_candidates",
                    [],
                )
                if isinstance(candidate, dict)
                and str(
                    candidate.get("url", "")
                    or ""
                ).strip()
            ]

            labels = []
            valid_candidates = []

            for candidate in candidates:

                title = str(
                    candidate.get(
                        "title",
                        "Untitled source",
                    )
                    or "Untitled source"
                ).strip()

                domain = str(
                    candidate.get(
                        "domain",
                        "",
                    )
                    or ""
                ).strip()

                labels.append(
                    f"{title} — {domain or 'web'}"
                )

                valid_candidates.append(candidate)

            if valid_candidates:

                choice = st.radio(
                    "Available sources",
                    options=labels,
                    key="web_source_choice",
                )

                selected_candidate = valid_candidates[
                    labels.index(choice)
                ]

                st.markdown(
                    f"**Title:** "
                    f"{selected_candidate.get('title', '')}"
                )

                st.markdown(
                    f"**Domain:** "
                    f"{selected_candidate.get('domain', '')}"
                )

                source_url = str(
                    selected_candidate.get(
                        "url",
                        "",
                    )
                    or ""
                ).strip()

                st.markdown(
                    f"**URL:** [{source_url}]({source_url})"
                )

                snippet = str(
                    selected_candidate.get(
                        "snippet",
                        "",
                    )
                    or ""
                ).strip()

                if snippet:
                    with st.expander(
                        "Search result preview",
                        expanded=False,
                    ):
                        st.write(snippet)

                approve_source_button = st.button(
                    "Approve Source & Continue",
                    type="primary",
                    use_container_width=True,
                    key="approve_web_source",
                )

                if approve_source_button:

                    add_log(
                        f"Teacher selected web source: "
                        f"{selected_candidate.get('title', '')}"
                    )

                    with st.spinner(
                        "Approving source, extracting content, and retrieving relevant context..."
                    ):
                        try:

                            approval_result = approve_source(
                                state,
                                selected_url=source_url,
                                teacher_id=state.get(
                                    "teacher_id",
                                    teacher_id,
                                ),
                                approval_comment=(
                                    "Teacher approved source "
                                    "for assessment generation."
                                ),
                            )

                            if not approval_result.success:
                                raise RuntimeError(
                                    approval_result.error_message
                                    or "Web source approval failed."
                                )

                            state.update(
                                approval_result.data or {}
                            )

                            add_log(
                                "Web source approval recorded."
                            )

                            # Fetch the approved source and run
                            # source-isolated RAG retrieval.
                            state = retrieve_source(
                                state
                            )

                            if state.get(
                                "retrieved_context"
                            ):

                                add_log(
                                    "Approved web source fetched and RAG context is ready."
                                )

                                workflow = get_workflow()

                                with st.spinner(
                                    "Assessment Agent is generating the web-grounded assessment..."
                                ):
                                    state = (
                                        workflow.generate_and_review(
                                            state
                                        )
                                    )

                                if state.get("status") == (
                                    "assessment_ready_for_review"
                                ):

                                    state[
                                        "assessment_review_status"
                                    ] = "passed"

                                    state[
                                        "assessment_review_feedback"
                                    ] = (
                                        "Review bypassed for "
                                        "end-to-end workflow test."
                                    )

                                    state["status"] = (
                                        "assessment_ready_for_teacher"
                                    )

                                    add_log(
                                        "Assessment Agent generated the web-grounded assessment."
                                    )

                            else:

                                clarification = str(
                                    state.get(
                                        "clarification_message",
                                        "",
                                    )
                                    or ""
                                )

                                if clarification:
                                    state[
                                        "error_message"
                                    ] = clarification

                                # The teacher has approved this URL.
                                # Preserve approval so the UI shows the
                                # approved source and offers retry.
                                state[
                                    "source_approved"
                                ] = True

                                state[
                                    "approval_status"
                                ] = "approved"

                                add_log(
                                    "Web source was approved, but RAG context was not retrieved."
                                )

                        except Exception as exc:

                            # Do not turn a downstream fetch/RAG
                            # failure into a blank/reset UI state.
                            state[
                                "source_approved"
                            ] = True

                            state[
                                "approval_status"
                            ] = "approved"

                            state[
                                "status"
                            ] = (
                                "assessment_generation_failed"
                            )

                            state[
                                "error_message"
                            ] = str(exc)

                            add_log(
                                f"Web source workflow failed: {exc}"
                            )

                    st.session_state.workflow_state = state
                    st.rerun()

            else:

                st.warning(
                    "Web search returned candidates, but no valid source URL is available."
                )

        # -------------------------------------------------
        # CASE 3: Web mode but nothing has been searched yet.
        # -------------------------------------------------
        else:

            st.info(
                "Web Search mode is active. Run Generate Assessment to search for web source candidates."
            )

    if state.get("questions"):

        display_questions(state)

        if state.get("status") == "assessment_ready_for_teacher":

            st.divider()

            st.subheader("Teacher Approval")

            st.write(

                "Review the generated assessment above. Nothing has been published yet."

            )

            approval_left, approval_right = st.columns(2)

            with approval_left:

                approve = st.button(

                    "Approve & Publish",

                    type="primary",

                    use_container_width=True,

                )

            with approval_right:

                reject = st.button(

                    "Reject",

                    use_container_width=True,

                )

            if approve:

                add_log("Teacher approved the generated assessment.")

                workflow = get_workflow()

                with st.spinner("Recording teacher approval..."):

                    try:

                        state = workflow.request_teacher_approval(

                            state,

                            teacher_id=state.get(

                                "teacher_id",

                                teacher_id,

                            ),

                            approved=True,

                        )

                    except Exception as exc:

                        state["status"] = "teacher_approval_failed"

                        state["error_message"] = str(exc)

                if state.get("status") == "assessment_approved":

                    add_log("Teacher approval recorded.")

                    add_log("Starting Google Form creation and publishing...")

                    with st.spinner("Creating and publishing Google Form..."):

                        state = workflow.create_and_publish_form(state)

                    if state.get("status") == "assessment_form_published":

                        add_log("Google Form created and published.")

                        add_log(

                            f"Responder URL: {state.get('responder_url', '')}"

                        )

                        add_log("Saving assessment to SQLite database...")

                        with st.spinner("Saving assessment to database..."):

                            state = workflow.save_assessment(

                                state,

                                teacher_id=state.get(

                                    "teacher_id",

                                    teacher_id,

                                ),

                                school_id=state.get(

                                    "school_id",

                                    school_id,

                                ),

                            )

                        if state.get("status") != "assessment_database_save_failed":

                            add_log(

                                f"Assessment saved with ID: {state.get('assessment_id')}"

                            )

                st.session_state.workflow_state = state

                st.rerun()

            if reject:

                add_log("Teacher rejected the generated assessment.")

                workflow = get_workflow()

                state = workflow.request_teacher_approval(

                    state,

                    teacher_id=state.get(

                        "teacher_id",

                        teacher_id,

                    ),

                    approved=False,

                )

                st.session_state.workflow_state = state

                st.rerun()

# =========================================================

# PROCESS MONITOR TAB

# =========================================================

with process_tab:

    st.subheader("Live Workflow Monitor")

    state = st.session_state.workflow_state

    current_status = state.get("status", "idle")

    if status_type(current_status) == "error":

        st.error(

            f"Workflow status: {status_label(current_status)}"

        )

        show_error(state)

    elif status_type(current_status) == "success":

        st.success(

            f"Workflow status: {status_label(current_status)}"

        )

    else:

        st.info(

            f"Workflow status: {status_label(current_status)}"

        )

    stages = [

        (

            "Teacher Input",

            "Request and assessment configuration received from teacher.",

            state.get("status") != "idle",

        ),

        (

            "Master / Source Routing",

            (

                "Teacher File Mode: uploaded file was ingested and relevant context was retrieved."

                if state.get("knowledge_source") == "teacher_file"

                else (

                    "Classroom Mode: Google Classroom material was retrieved."

                    if state.get("knowledge_source") == "google_classroom"

                    else (

                        "Web Search Mode: waiting for teacher to approve a source."

                        if state.get("knowledge_source") == "web_search"

                        and not state.get("retrieved_context")

                        else (

                            "Web Search Mode: approved source was retrieved through RAG."

                            if state.get("knowledge_source") == "web_search"

                            else "Test Mode: source routing is intentionally bypassed."

                        )

                    )

                )

            ),

            (

                bool(state.get("retrieved_context"))

                if state.get("generation_mode") == "source_grounded"

                else True

            ),

        ),

        (

            "Assessment Agent",

            "Task routed through capability assessment.create and the Assessment Agent generated the MCQs.",

            bool(state.get("questions")),

        ),

        (

            "Assessment Review",

            "Bypassed for this end-to-end workflow test; output is accepted as-is.",

            state.get("assessment_review_status") == "passed",

        ),

        (

            "Teacher Approval",

            "Human approval is required before publishing.",

            state.get("approval_status") == "approved",

        ),

        (

            "Google Forms",

            "Google Form created and published through the Forms Tool.",

            bool(state.get("form_id")) and bool(

                state.get("form_is_published")

            ),

        ),

        (

            "Database",

            "Assessment and its questions saved into SQLite.",

            bool(state.get("assessment_id")),

        ),

        (

            "Student Email Delivery",

            "Student emails resolved from DB and assessment link sent through Gmail.",

            state.get("status") == "assessment_sent_to_students",

        ),

    ]

    for title, description, complete in stages:

        if complete:

            st.success(f"âœ“ {title}")

        else:

            st.info(f"â—‹ {title}")

        st.caption(description)

    st.divider()

    show_logs()

# =========================================================

# RESULT TAB

# =========================================================

with result_tab:

    st.subheader("Assessment Result")

    state = st.session_state.workflow_state

    if state.get("questions"):

        display_questions(state)

    if state.get("generation_mode") == "source_grounded":

        st.divider()

        st.subheader("Knowledge Source")

        source_cols = st.columns(4)

        source_cols[0].write(

            f"**Source:** `{state.get('knowledge_source', '')}`"

        )

        source_cols[1].write(

            f"**Source status:** `{state.get('source_status', '')}`"

        )

        source_cols[2].write(

            f"**Source approved:** `{state.get('source_approved', False)}`"

        )

        if state.get("knowledge_source") == "web_search":

            source_title = str(

                state.get("selected_source", {}).get("title", "")

                or "Web source"

            )

            source_cols[3].write(

                f"**Source:** `{source_title}`"

            )

            source_url = str(

                state.get("selected_source", {}).get("url", "")

                or state.get("source_url", "")

            ).strip()

            if source_url:

                st.link_button(

                    "Open Approved Web Source",

                    source_url,

                    use_container_width=False,

                )

        else:

            source_cols[3].write(

                f"**File:** `{state.get('uploaded_file_name', '')}`"

            )

            if state.get("uploaded_file_name"):

                st.info(

                    f"Teacher source file used: **{state.get('uploaded_file_name')}**"

                )

        if state.get("retrieved_context"):

            with st.expander(

                (

                    "Retrieved teacher-file context"

                    if state.get("knowledge_source") == "teacher_file"

                    else (

                        "Retrieved web-source context"

                        if state.get("knowledge_source") == "web_search"

                        else "Retrieved Classroom context"

                    )

                ),

                expanded=False,

            ):

                st.text(state.get("retrieved_context", ""))

    if state.get("form_id"):

        st.divider()

        st.subheader("Google Form")

        form_cols = st.columns(3)

        form_cols[0].write(

            f"**Form ID:** `{state.get('form_id')}`"

        )

        form_cols[1].write(

            f"**Published:** `{state.get('form_is_published')}`"

        )

        form_cols[2].write(

            f"**Accepting Responses:** `{state.get('form_accepting_responses')}`"

        )

        responder_url = state.get("responder_url")

        edit_url = state.get("edit_url")

        if responder_url:

            st.link_button(

                "Open Student Form",

                responder_url,

                use_container_width=True,

            )

        if edit_url:

            st.link_button(

                "Open Form Editor",

                edit_url,

                use_container_width=True,

            )

    if state.get("assessment_id"):

        st.divider()

        st.subheader("Database")

        st.write(

            f"Assessment ID: **{state.get('assessment_id')}**"

        )

    if state.get("status") == "assessment_form_published":

        st.divider()

        st.subheader("Student Delivery")

        st.write(

            "The Form is published, but it has not been sent to students yet."

        )

        st.info(

            f"Delivery target: **{state.get('student_class_level', '')} / {state.get('section', '')}**"

        )

        send_left, send_right = st.columns(2)

        with send_left:

            send_students = st.button(

                "Send to Students",

                type="primary",

                use_container_width=True,

            )

        with send_right:

            keep_unsent = st.button(

                "Do Not Send",

                use_container_width=True,

            )

        if send_students:

            workflow = get_workflow()

            add_log("Teacher approved student delivery.")

            add_log("Looking up student email addresses from database...")

            with st.spinner("Finding students and sending assessment email..."):

                try:

                    state = workflow.request_student_send(

                        state,

                        school_id=state.get(

                            "school_id",

                            school_id,

                        ),

                        class_level=state.get(

                            "student_class_level",

                            student_class_level,

                        ),

                        section=state.get(

                            "section",

                            section,

                        ),

                        send_to_students=True,

                    )

                except Exception as exc:

                    state["status"] = "student_email_send_failed"

                    state["error_message"] = str(exc)

            if state.get("status") == "assessment_sent_to_students":

                add_log(

                    f"Email delivery finished: {state.get('student_email_sent', 0)} sent, {state.get('student_email_failed', 0)} failed."

                )

            else:

                add_log(

                    f"Student delivery ended with status: {state.get('status')}"

                )

            st.session_state.workflow_state = state

            st.rerun()

        if keep_unsent:

            add_log("Teacher chose not to send the assessment to students.")

            state["status"] = "assessment_created_not_sent"

            st.session_state.workflow_state = state

            st.rerun()

    if state.get("status") == "assessment_sent_to_students":

        st.divider()

        st.success("Assessment successfully delivered to students.")

        cols = st.columns(3)

        cols[0].metric(

            "Recipients",

            state.get("student_email_total", 0),

        )

        cols[1].metric(

            "Emails Sent",

            state.get("student_email_sent", 0),

        )

        cols[2].metric(

            "Failed",

            state.get("student_email_failed", 0),

        )

    show_evaluation_dashboard(state)

    show_error(state)
