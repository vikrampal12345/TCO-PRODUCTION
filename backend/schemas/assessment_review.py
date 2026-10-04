from pydantic import BaseModel, Field


class QuestionReview(BaseModel):
    """
    Review result for one MCQ.
    """

    question_number: int = Field(
        ge=1
    )

    correct: bool

    issue: str = ""

    suggested_correction: str = ""


class AssessmentReview(BaseModel):
    """
    Structured output produced by the
    Assessment Review Agent.
    """

    approved: bool

    summary: str = ""

    issues: list[str] = Field(
        default_factory=list
    )

    question_reviews: list[QuestionReview] = Field(
        default_factory=list
    )