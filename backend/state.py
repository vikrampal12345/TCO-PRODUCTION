from typing import Any, TypedDict

from backend.core.task import Task


class TCOState(
    TypedDict,
    total=False,
):

    # ========================================================
    # REQUEST / EXECUTION CONTEXT
    # ========================================================

    request_id: str

    teacher_id: str

    school_id: str

    conversation_id: str

    teacher_request: str

    # ========================================================
    # MASTER AGENT DECISION
    # ========================================================

    intent: str

    language: str

    next_action: str

    required_capability: str | None

    # ========================================================
    # CURRENT TASK
    # ========================================================

    current_task: Task | None

    # ========================================================
    # ASSESSMENT REQUIREMENTS
    # ========================================================

    class_level: str

    subject: str

    chapter: str

    topic: str

    marks: int

    question_count: int

    student_name: str

    missing_information: list[str]

    clarification_message: str

    # ========================================================
    # GENERATION POLICY
    # ========================================================

    generation_mode: str

    source_preference: str

    # ========================================================
    # SOURCE / RESEARCH
    # ========================================================

    source: str

    requested_source: str

    source_url: str

    source_available: bool

    source_status: str

    source_candidates: list[dict[str, Any]]

    selected_source: dict[str, Any]

    source_approved: bool

    retrieved_context: str

    source_references: list[str]

    reference_questions: list

    # ========================================================
    # GOOGLE CLASSROOM
    # ========================================================

    classroom_course_id: str

    classroom_material_id: str

    classroom_drive_file_id: str

    classroom_attachment_title: str

    # ========================================================
    # ASSESSMENT OUTPUT
    # ========================================================

    questions: list

    answer_key: list

    marking_scheme: list

    # ========================================================
    # VALIDATION
    # ========================================================

    validation_status: str

    validation_errors: list[str]

    # ========================================================
    # HUMAN-IN-THE-LOOP
    # ========================================================

    approval_required: bool

    approval_type: str

    approval_status: str

    approved_by: str

    approval_comment: str

    approved_at: str

    # ========================================================
    # DOWNSTREAM
    # ========================================================

    assignment_id: str

    submissions: list

    evaluation_results: list

    # ========================================================
    # STATUS
    # ========================================================

    status: str

    assessment_message: str

    # ========================================================
    # ERROR
    # ========================================================

    error_code: str

    error_message: str

    # ========================================================
    # METADATA
    # ========================================================

    metadata: dict[str, Any]

    # ========================================================
    # ASSESSMENT REVIEW
    # ========================================================

    assessment_review_status: str

    assessment_review_feedback: str

    assessment_review_attempts: int

    assessment_max_review_attempts: int