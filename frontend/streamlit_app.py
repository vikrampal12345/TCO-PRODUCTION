from __future__ import annotations

from datetime import datetime
from typing import Any

import streamlit as st

from backend.core.bootstrap import build_default_registry
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
    "class_level": "",
    "student_class_level": "",
    "subject": "",
    "chapter": "",
    "topic": "",
    "marks": 0,
    "question_count": 0,
    "generation_mode": "llm_generated",
    "source_preference": "general_knowledge",
    "requested_source": "",
    "source_url": "",
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
    add_log("Workflow reset. Ready for a new assessment.")


def status_label(status: str) -> str:
    labels = {
        "idle": "Ready",
        "assessment_generation_failed": "Generation failed",
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
        ).replace("\\n", "\n")

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
            f"Teacher view — answer for Q{index}",
            expanded=False,
        ):
            st.write(
                f"Correct option: **{question.get('correct_option', 'N/A')}**"
            )


def show_error(state: dict[str, Any]) -> None:
    error = state.get("error_message")
    if error:
        st.error(error)


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
) -> dict[str, Any]:
    return {
        "request_id": f"streamlit_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "teacher_id": teacher_id,
        "school_id": school_id,
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
        "generation_mode": "llm_generated",
        "requested_source": "",
        "source_preference": "general_knowledge",
        "source_url": "",
        "section": section,
        "missing_information": [],
        "status": "starting",
    }


# =========================================================
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
        value="Python",
    )

    chapter = st.text_input(
        "Chapter",
        value="Python Basics",
    )

    topic = st.text_input(
        "Topic",
        value="Python Basics",
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
        value=5,
        step=1,
    )

    st.caption(
        "Current workflow mode: AI general knowledge. "
        "The generated LLM output is passed through as-is."
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
    "<div class='tco-title'>TCO — Teacher Co-Worker</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='tco-subtitle'>Create an assessment, approve it, publish it, save it, and deliver it to students — while watching every workflow step.</div>",
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
            "Create a 5-question, 5-mark MCQ assessment on "
            "Python basics for BTech 1st Year students."
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
        )

        st.session_state.workflow_state = state
        st.session_state.logs = []

        add_log("Teacher submitted a new assessment request.")
        add_log(
            f"Request: {teacher_request.strip()}"
        )
        add_log("Routing task to capability: assessment.create")
        add_log("Calling local LLM through Assessment Agent...")

        workflow = get_workflow()

        with st.spinner("Assessment Agent is generating the assessment..."):
            try:
                state = workflow.generate_and_review(state)
            except Exception as exc:
                state["status"] = "assessment_generation_failed"
                state["error_message"] = str(exc)
                add_log(
                    f"Assessment generation failed: {exc}"
                )
            else:
                add_log("Assessment Agent finished generation.")
                add_log(
                    "Review Agent is bypassed for this workflow test; LLM output is accepted as-is."
                )
                if state.get("status") == "assessment_ready_for_teacher":
                    add_log(
                        "Assessment is waiting for teacher approval."
                    )

        st.session_state.workflow_state = state
        st.rerun()

    state = st.session_state.workflow_state

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
            "Assessment Agent",
            "Task routed through capability assessment.create and local LLM generated the MCQs.",
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
            st.success(f"✓ {title}")
        else:
            st.info(f"○ {title}")
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

    show_error(state)
