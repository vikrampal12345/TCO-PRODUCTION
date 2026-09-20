from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI

from backend.config import GEMINI_API_KEY
from backend.state import TCOState
from backend.prompts.assessment_agent_prompt import (
    ASSESSMENT_AGENT_SYSTEM_PROMPT,
)


# ============================================================
# Question Schema
# ============================================================

class AssessmentQuestion(BaseModel):
    question_number: int = Field(
        description="Question number starting from 1."
    )

    question: str = Field(
        description="The assessment question."
    )

    marks: int = Field(
        description="Marks assigned to this question."
    )

    expected_answer: str = Field(
        description="Expected answer or answer guideline."
    )

    difficulty: str = Field(
        description="Difficulty level: easy, medium, or hard."
    )

    # IMPORTANT:
    # This is informational output only.
    # We will NOT trust the model for the final source list.
    source_reference: str | None = Field(
        default=None,
        description="Source reference supporting this question."
    )


# ============================================================
# Assessment Output Schema
# ============================================================

class AssessmentOutput(BaseModel):
    status: str = Field(
        description=(
            "success or insufficient_source_material"
        )
    )

    questions: list[AssessmentQuestion] = Field(
        default_factory=list
    )

    answer_key: list[str] = Field(
        default_factory=list
    )

    marking_scheme: list[str] = Field(
        default_factory=list
    )

    # Kept in schema for model compatibility,
    # but final references will come from state/RAG.
    source_references: list[str] = Field(
        default_factory=list
    )

    message: str | None = Field(
        default=None
    )


# ============================================================
# Gemini Model
# ============================================================

model = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    google_api_key=GEMINI_API_KEY,
)

structured_model = model.with_structured_output(
    AssessmentOutput
)


# ============================================================
# Assessment Agent
# ============================================================

def assessment_agent(state: TCOState) -> TCOState:
    """
    Generate an assessment based on the selected generation mode.

    source_grounded:
        Use only retrieved/approved source material.

    llm_generated:
        Use general LLM knowledge because the teacher
        explicitly allowed AI generation.
    """

    topic = state.get("topic")
    question_count = state.get("question_count")
    marks = state.get("marks")

    retrieved_context = state.get(
        "retrieved_context",
        ""
    )

    reference_questions = state.get(
        "reference_questions",
        []
    )

    generation_mode = state.get(
        "generation_mode",
        "source_grounded"
    )

    # ========================================================
    # Required topic validation
    # ========================================================

    if not topic:

        return {
            **state,
            "status": "waiting_for_teacher",
            "clarification_message": (
                "Please provide the exact chapter name or topic "
                "for the assessment."
            ),
        }

    # ========================================================
    # Source-grounded validation
    # ========================================================

    if generation_mode == "source_grounded":

        if (
            not retrieved_context.strip()
            and not reference_questions
        ):

            return {
                **state,
                "questions": [],
                "answer_key": [],
                "marking_scheme": [],
                "status": "insufficient_source_material",
                "clarification_message": (
                    f"I don't have enough approved source material "
                    f"for {topic}. Please provide notes/reference "
                    "material or explicitly allow AI-generated "
                    "content."
                ),
            }

    # ========================================================
    # Prepare reference questions
    # ========================================================

    reference_text = "\n".join(
        f"- {question}"
        for question in reference_questions
    )

    # ========================================================
    # Prepare marks instruction
    # ========================================================

    marks_instruction = (
        str(marks)
        if marks is not None
        else "Not specified"
    )

    question_count_instruction = (
        str(question_count)
        if question_count is not None
        else "Not specified"
    )

    # ========================================================
    # Prompt
    # ========================================================

    user_prompt = f"""
{ASSESSMENT_AGENT_SYSTEM_PROMPT}

============================================================
CURRENT ASSESSMENT REQUEST
============================================================

Topic:
{topic}

Number of questions:
{question_count_instruction}

Total marks:
{marks_instruction}

Generation mode:
{generation_mode}

============================================================
RETRIEVED SOURCE MATERIAL
============================================================

{retrieved_context if retrieved_context else "No retrieved source material."}

============================================================
REFERENCE QUESTIONS
============================================================

{reference_text if reference_text else "No reference questions."}

============================================================
IMPORTANT
============================================================

For source_grounded mode:

- Use only the supplied retrieved source material.
- Every question must be supported by the retrieved material.
- Do not introduce unsupported concepts.
- Do not use outside knowledge.
- Do not fabricate sources.
- If the material is insufficient, return:
  status = "insufficient_source_material"

For llm_generated mode:

- The teacher explicitly allowed AI generation.
- General knowledge may be used.
- Keep the content relevant to the topic.

Generate the assessment now.
"""

    # ========================================================
    # LLM call
    # ========================================================

    result = structured_model.invoke(
        user_prompt
    )

    # ========================================================
    # IMPORTANT:
    # Preserve RAG source references from State
    # ========================================================

    actual_source_references = state.get(
        "source_references",
        []
    )

    # ========================================================
    # Update state
    # ========================================================

    updated_state: TCOState = {
        **state,

        "questions": [
            question.model_dump()
            for question in result.questions
        ],

        "answer_key": result.answer_key,

        "marking_scheme": result.marking_scheme,

        # DO NOT trust the LLM for final source list.
        "source_references": (
            actual_source_references
        ),

        "status": result.status,
    }

    if result.message:

        updated_state["assessment_message"] = (
            result.message
        )

    return updated_state