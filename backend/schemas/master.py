from typing import Literal

from pydantic import BaseModel, Field


class MasterDecision(BaseModel):
    """
    Structured decision produced by the Master Agent.

    The Master Agent understands the teacher's request
    and identifies the capability required to fulfill it.

    It does not perform the specialist work itself.
    """

    # ---------------------------------------------------------
    # REQUEST UNDERSTANDING
    # ---------------------------------------------------------

    intent: Literal[
        "assessment",
        "attendance",
        "analytics",
        "teaching",
        "student_support",
        "communication",
        "evaluation",
        "copy_checking",
        "result",
        "source_request",
        "summarization",
        "unknown",
    ] = "unknown"

    language: Literal[
        "english",
        "hinglish",
        "hindi",
    ] = "english"

    # ---------------------------------------------------------
    # REQUIRED CAPABILITY
    # ---------------------------------------------------------

    required_capability: str | None = None

    # ---------------------------------------------------------
    # COMMON REQUEST CONTEXT
    # ---------------------------------------------------------

    class_level: str | None = None
    subject: str | None = None
    chapter: str | None = None
    topic: str | None = None

    student_name: str | None = None

    # ---------------------------------------------------------
    # ASSESSMENT REQUIREMENTS
    # ---------------------------------------------------------

    marks: int | None = Field(
        default=None,
        ge=1,
    )

    question_count: int | None = Field(
        default=None,
        ge=1,
    )

    # ---------------------------------------------------------
    # GENERATION POLICY
    # ---------------------------------------------------------

    generation_mode: Literal[
        "source_grounded",
        "llm_generated",
    ] = "source_grounded"

    # ---------------------------------------------------------
    # SOURCE INFORMATION
    # ---------------------------------------------------------

    requested_source: str | None = None

    source_preference: Literal[
        "teacher_provided",
        "specific_source",
        "web_search",
        "general_knowledge",
        "unknown",
    ] = "unknown"

    source_url: str | None = None

    # ---------------------------------------------------------
    # TASK REQUIREMENTS
    # ---------------------------------------------------------

    missing_information: list[str] = Field(
        default_factory=list
    )

    clarification_message: str = ""