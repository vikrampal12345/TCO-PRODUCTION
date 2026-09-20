from typing import TypedDict


class TCOState(TypedDict, total=False):

    # ============================================================
    # Teacher Input
    # ============================================================
    teacher_request: str

    # ============================================================
    # Master Agent
    # ============================================================
    intent: str
    language: str
    next_action: str

    # ============================================================
    # Extracted Information
    # ============================================================
    topic: str
    marks: int
    question_count: int
    student_name: str

    # ============================================================
    # Clarification
    # ============================================================
    missing_information: list[str]
    clarification_message: str

    # ============================================================
    # Source / RAG
    # ============================================================
    generation_mode: str
    source: str
    source_available: bool
    source_status: str
    retrieved_context: str
    reference_questions: list[str]
    source_references: list[str]

    # ============================================================
    # Assessment
    # ============================================================
    questions: list
    answer_key: list
    marking_scheme: list

    # ============================================================
    # Human Approval
    # ============================================================
    approved: bool

    # ============================================================
    # Google Classroom
    # ============================================================
    assignment_id: str
    submissions: list

    # ============================================================
    # Evaluation
    # ============================================================
    evaluation_results: list

    # ============================================================
    # Workflow
    # ============================================================
    status: str
    assessment_message: str