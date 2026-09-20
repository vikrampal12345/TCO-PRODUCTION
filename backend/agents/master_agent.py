from typing import Literal

from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI

from backend.config import GEMINI_API_KEY
from backend.state import TCOState
from backend.prompts.master_agent_prompt import (
    MASTER_AGENT_SYSTEM_PROMPT,
)


# ============================================================
# Structured Output
# ============================================================

class MasterDecision(BaseModel):

    intent: Literal[
        "assessment",
        "evaluation",
        "attendance",
        "analytics",
        "ppt",
        "classroom",
        "other",
    ] = Field(
        description="The main task the teacher wants TCO to perform."
    )

    language: Literal[
        "english",
        "hinglish",
        "other",
    ] = Field(
        description="The language style used by the teacher."
    )

    topic: str | None = Field(
        default=None,
        description=(
            "Exact subject, chapter, or topic explicitly provided "
            "by the teacher. Never invent it."
        ),
    )

    marks: int | None = Field(
        default=None,
        description=(
            "Total assessment marks explicitly provided "
            "by the teacher."
        ),
    )

    question_count: int | None = Field(
        default=None,
        description=(
            "Number of questions explicitly provided "
            "by the teacher."
        ),
    )

    student_name: str | None = Field(
        default=None,
        description=(
            "Student name explicitly provided by the teacher."
        ),
    )

    generation_mode: Literal[
        "source_grounded",
        "llm_generated",
    ] = Field(
        default="source_grounded",
        description=(
            "source_grounded by default. "
            "llm_generated only when the teacher explicitly "
            "allows AI-generated content."
        ),
    )

    missing_information: list[str] = Field(
        default_factory=list,
        description=(
            "Required information missing from the request."
        ),
    )

    next_action: Literal[
        "ask_teacher",
        "assessment",
        "evaluation",
        "attendance",
        "analytics",
        "ppt",
        "classroom",
        "other",
    ] = Field(
        description="The next workflow action TCO should take."
    )

    clarification_message: str | None = Field(
        default=None,
        description=(
            "Short natural-language clarification question "
            "for the teacher."
        ),
    )


# ============================================================
# Gemini Model
# ============================================================

model = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    google_api_key=GEMINI_API_KEY,
)

structured_model = model.with_structured_output(
    MasterDecision
)


# ============================================================
# Master Agent
# ============================================================

def master_agent(state: TCOState) -> TCOState:
    """
    Understand the teacher's natural-language request,
    extract explicitly provided information, validate required
    assessment information, and decide the next workflow action.
    """

    teacher_request = state["teacher_request"]

    prompt = f"""
{MASTER_AGENT_SYSTEM_PROMPT}

============================================================
TEACHER REQUEST
============================================================

{teacher_request}
"""

    decision = structured_model.invoke(prompt)

    updated_state: TCOState = {
        **state,
        "intent": decision.intent,
        "language": decision.language,
        "generation_mode": decision.generation_mode,
        "missing_information": list(
            decision.missing_information
        ),
        "status": "intent_identified",
    }

    # ========================================================
    # Extract available information
    # ========================================================

    if decision.topic is not None:
        updated_state["topic"] = decision.topic

    if decision.marks is not None:
        updated_state["marks"] = decision.marks

    if decision.question_count is not None:
        updated_state["question_count"] = (
            decision.question_count
        )

    if decision.student_name is not None:
        updated_state["student_name"] = (
            decision.student_name
        )

    # ========================================================
    # Strict Assessment Validation
    # ========================================================

    if decision.intent == "assessment":

        missing = []

        if not decision.topic:
            missing.append("topic")

        if decision.question_count is None:
            missing.append("question_count")

        if decision.marks is None:
            missing.append("marks")

        # ----------------------------------------------------
        # Required assessment information is missing
        # ----------------------------------------------------

        if missing:

            updated_state["missing_information"] = missing

            updated_state["next_action"] = (
                "ask_teacher"
            )

            # -----------------------------------------------
            # Build natural clarification message
            # -----------------------------------------------

            if missing == ["topic"]:
                message = (
                    "Please provide the exact chapter name "
                    "or topic for the assessment."
                )

            elif missing == ["question_count"]:
                message = (
                    "How many questions should the "
                    "assessment contain?"
                )

            elif missing == ["marks"]:
                message = (
                    "How many total marks should the "
                    "assessment carry?"
                )

            else:
                missing_labels = []

                if "topic" in missing:
                    missing_labels.append(
                        "exact chapter/topic"
                    )

                if "question_count" in missing:
                    missing_labels.append(
                        "number of questions"
                    )

                if "marks" in missing:
                    missing_labels.append(
                        "total marks"
                    )

                message = (
                    "Please provide "
                    + ", ".join(missing_labels)
                    + " for the assessment."
                )

            updated_state["clarification_message"] = (
                message
            )

            updated_state["status"] = (
                "waiting_for_teacher"
            )

            return updated_state

        # ----------------------------------------------------
        # All required assessment information exists
        # ----------------------------------------------------

        updated_state["next_action"] = (
            "assessment"
        )

        updated_state["missing_information"] = []

        if decision.clarification_message:
            updated_state["clarification_message"] = (
                decision.clarification_message
            )

        return updated_state

    # ========================================================
    # Non-assessment intents
    # ========================================================

    updated_state["next_action"] = (
        decision.next_action
    )

    if decision.clarification_message:
        updated_state["clarification_message"] = (
            decision.clarification_message
        )

    return updated_state