from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from backend.core.base_agent import BaseAgent
from backend.core.model_provider import get_chat_model


# ============================================================
# STRUCTURED LLM OUTPUT FOR SUBJECTIVE EVALUATION
# ============================================================


class SubjectiveEvaluation(BaseModel):
    marks_awarded: float = Field(
        ge=0,
        description="Marks awarded to the student's answer.",
    )
    correctness: str = Field(
        description="correct, partially_correct, incorrect, or unclear",
    )
    feedback: str = Field(
        description="Brief teacher-facing feedback.",
    )
    missing_points: list[str] = Field(
        default_factory=list,
        description="Important points missing from the answer.",
    )
    review_required: bool = False


# ============================================================
# EVALUATION AGENT
# ============================================================


class EvaluationAgent(BaseAgent):
    """
    Evaluates a student submission against an approved assessment.

    IMPORTANT ARCHITECTURE RULE:

    The agent is SOURCE-AGNOSTIC.

    It does not care whether the submission came from:
        - Google Forms
        - scanned handwritten copy
        - typed/manual submission
        - another future assessment channel

    Every source must first be normalized into:

        {
            "question_id": "...",
            "answer": "...",
            "confidence": 0.98,              # optional
            "source_locator": {...},        # optional
        }

    Therefore a future OCR/Vision tool can be added without
    changing the evaluation contract.
    """

    name = "evaluation_agent"

    description = (
        "Evaluates objective and subjective student submissions "
        "against an approved assessment answer key and rubric."
    )

    capabilities = ("evaluation.check",)

    def __init__(
        self,
        model: Any | None = None,
    ) -> None:
        self.model = model or get_chat_model().with_structured_output(
            SubjectiveEvaluation
        )

    # ========================================================
    # PUBLIC AGENT ENTRY POINT
    # ========================================================

    def run(
        self,
        state: dict[str, Any],
        task: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Evaluate one submission and return the updated TCO state.

        Expected assessment information can come from:

            state["assessment"]
            OR
            state["questions"] + state["answer_key"] + state["marking_scheme"]

        Expected submission information can come from:

            state["current_submission"]
            OR
            state["submission"]
            OR
            state["submissions"][0]

        The method intentionally does NOT perform:
            OCR
            database writes
            email sending
            student identification

        Those remain separate responsibilities.
        """

        task = task or {}

        assessment = (
            state.get("assessment")
            or task.get("assessment")
            or {
                "questions": state.get("questions", []),
                "answer_key": state.get("answer_key", []),
                "marking_scheme": state.get(
                    "marking_scheme",
                    [],
                ),
            }
        )

        submission = (
            state.get("current_submission")
            or state.get("submission")
        )

        if submission is None:
            submissions = state.get("submissions", [])
            if submissions:
                submission = submissions[0]

        if not isinstance(submission, dict):
            return {
                **state,
                "status": "evaluation_failed",
                "error_code": "SUBMISSION_MISSING",
                "error_message": (
                    "No student submission was provided for evaluation."
                ),
            }

        questions = assessment.get("questions", []) or []
        answer_key = assessment.get("answer_key", []) or []
        marking_scheme = assessment.get("marking_scheme", []) or []

        if not questions and not answer_key:
            return {
                **state,
                "status": "evaluation_failed",
                "error_code": "ASSESSMENT_KEY_MISSING",
                "error_message": (
                    "Assessment questions/answer key are required "
                    "before evaluation."
                ),
            }

        try:
            result = self.evaluate_submission(
                questions=questions,
                answer_key=answer_key,
                marking_scheme=marking_scheme,
                submission=submission,
                submission_source=(
                    state.get("submission_source")
                    or submission.get("submission_source")
                    or "unknown"
                ),
            )

        except Exception as exc:
            return {
                **state,
                "status": "evaluation_failed",
                "error_code": "EVALUATION_FAILED",
                "error_message": str(exc),
            }

        return {
            **state,
            "evaluation_result": result,
            "evaluation_results": [result],
            "status": (
                "evaluation_requires_review"
                if result["review_required"]
                else "evaluation_complete"
            ),
            "evaluation_status": result["evaluation_status"],
        }

    # ========================================================
    # SOURCE-AGNOSTIC EVALUATION
    # ========================================================

    def evaluate_submission(
        self,
        *,
        questions: list[dict[str, Any]],
        answer_key: list[dict[str, Any]],
        marking_scheme: list[dict[str, Any]],
        submission: dict[str, Any],
        submission_source: str = "unknown",
    ) -> dict[str, Any]:
        """
        Evaluate a normalized submission.

        This is the core contract shared by Google Forms and
        future scan/OCR workflows.
        """

        answers = self.normalize_submission_answers(
            submission.get("answers", [])
        )

        question_map = self._build_question_map(
            questions=questions,
            answer_key=answer_key,
            marking_scheme=marking_scheme,
        )

        answer_map = {
            str(item["question_id"]): item
            for item in answers
            if item.get("question_id")
        }

        question_results: list[dict[str, Any]] = []

        obtained_marks = 0.0
        total_marks = 0.0
        correct_answers = 0
        wrong_answers = 0
        unanswered = 0
        review_required = False

        for question_id, question in question_map.items():
            max_marks = self._question_marks(question)

            total_marks += max_marks

            student_answer = answer_map.get(question_id)

            if student_answer is None:
                question_results.append(
                    {
                        "question_id": question_id,
                        "question": question.get("question", ""),
                        "question_type": self._question_type(question),
                        "student_answer": "",
                        "marks_awarded": 0.0,
                        "max_marks": max_marks,
                        "status": "unanswered",
                        "feedback": "",
                    }
                )
                unanswered += 1
                continue

            answer_text = self._answer_to_text(student_answer)

            if not answer_text.strip():
                question_results.append(
                    {
                        "question_id": question_id,
                        "question": question.get("question", ""),
                        "question_type": self._question_type(question),
                        "student_answer": "",
                        "marks_awarded": 0.0,
                        "max_marks": max_marks,
                        "status": "unanswered",
                        "feedback": "",
                        "confidence": student_answer.get("confidence"),
                        "source_locator": student_answer.get(
                            "source_locator"
                        ),
                    }
                )
                unanswered += 1
                continue

            qtype = self._question_type(question)

            if self._is_objective(qtype, question):
                evaluated = self._evaluate_objective_question(
                    question=question,
                    student_answer=student_answer,
                    max_marks=max_marks,
                )
            else:
                evaluated = self._evaluate_subjective_question(
                    question=question,
                    student_answer=student_answer,
                    max_marks=max_marks,
                )

            question_results.append(evaluated)

            marks_awarded = float(
                evaluated.get("marks_awarded", 0.0)
            )
            obtained_marks += marks_awarded

            status = evaluated.get("status")

            if status == "correct":
                correct_answers += 1
            elif status == "wrong":
                wrong_answers += 1
            elif status == "partially_correct":
                review_required = (
                    review_required
                    or bool(
                        evaluated.get(
                            "review_required",
                            False,
                        )
                    )
                )
            elif status in {
                "unclear",
                "requires_review",
            }:
                review_required = True

        percentage = (
            round(
                (obtained_marks / total_marks) * 100,
                2,
            )
            if total_marks
            else 0.0
        )

        evaluation_status = (
            "requires_review"
            if review_required
            else "complete"
        )

        return {
            "submission_source": submission_source,
            "submission_id": submission.get("submission_id"),
            "student_id": submission.get("student_id"),
            "student_name": submission.get("student_name"),
            "student_email": submission.get("student_email"),
            "submitted_at": submission.get("submitted_at"),
            "obtained_marks": round(obtained_marks, 2),
            "total_marks": round(total_marks, 2),
            "percentage": percentage,
            "correct_answers": correct_answers,
            "wrong_answers": wrong_answers,
            "unanswered": unanswered,
            "review_required": review_required,
            "evaluation_status": evaluation_status,
            "question_results": question_results,
        }

    # ========================================================
    # NORMALIZATION LAYER
    # ========================================================

    @staticmethod
    def normalize_submission_answers(
        answers: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        """
        Normalize answers from any source into one contract.

        Supported input examples:

        Google Forms:
            {
                "question_id": "q1",
                "values": ["Option A"],
            }

        Scan/OCR/Vision:
            {
                "question_id": "q1",
                "text": "Option A",
                "confidence": 0.97,
                "source_locator": {
                    "page": 2
                }
            }

        Manual/future source:
            {
                "question_id": "q1",
                "answer": "Option A"
            }
        """

        normalized: list[dict[str, Any]] = []

        for item in answers or []:
            if not isinstance(item, dict):
                continue

            question_id = (
                item.get("question_id")
                or item.get("item_id")
                or item.get("id")
            )

            if not question_id:
                continue

            if "answer" in item:
                answer = item.get("answer")
            elif "text" in item:
                answer = item.get("text")
            elif "values" in item:
                answer = item.get("values")
            else:
                answer = ""

            normalized.append(
                {
                    "question_id": str(question_id),
                    "answer": answer,
                    "confidence": item.get("confidence"),
                    "source_locator": item.get(
                        "source_locator"
                    ),
                }
            )

        return normalized

    # ========================================================
    # QUESTION / KEY MERGING
    # ========================================================

    @classmethod
    def _build_question_map(
        cls,
        *,
        questions: list[dict[str, Any]],
        answer_key: list[dict[str, Any]],
        marking_scheme: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """
        Merge question definitions, answer key and marking scheme.

        This keeps the evaluation agent independent from exactly
        where the assessment metadata came from.
        """

        result: dict[str, dict[str, Any]] = {}

        for index, question in enumerate(questions):
            if not isinstance(question, dict):
                continue

            question_id = (
                question.get("question_id")
                or question.get("id")
                or question.get("item_id")
                or f"question_{index + 1}"
            )

            result[str(question_id)] = {
                **question,
                "question_id": str(question_id),
            }

        for index, key in enumerate(answer_key):
            if not isinstance(key, dict):
                continue

            question_id = (
                key.get("question_id")
                or key.get("id")
                or key.get("item_id")
            )

            if not question_id and index < len(questions):
                base = questions[index]
                question_id = (
                    base.get("question_id")
                    or base.get("id")
                    or base.get("item_id")
                    or f"question_{index + 1}"
                )

            if not question_id:
                continue

            question_id = str(question_id)

            result.setdefault(
                question_id,
                {
                    "question_id": question_id,
                }
            ).update(key)

        for index, scheme in enumerate(marking_scheme):
            if not isinstance(scheme, dict):
                continue

            question_id = (
                scheme.get("question_id")
                or scheme.get("id")
                or scheme.get("item_id")
            )

            if not question_id and index < len(questions):
                base = questions[index]
                question_id = (
                    base.get("question_id")
                    or base.get("id")
                    or base.get("item_id")
                    or f"question_{index + 1}"
                )

            if not question_id:
                continue

            result.setdefault(
                str(question_id),
                {
                    "question_id": str(question_id),
                }
            ).update(scheme)

        return result

    # ========================================================
    # OBJECTIVE EVALUATION
    # ========================================================

    def _evaluate_objective_question(
        self,
        *,
        question: dict[str, Any],
        student_answer: dict[str, Any],
        max_marks: float,
    ) -> dict[str, Any]:
        accepted_answers = self._accepted_answers(question)

        student_text = self._answer_to_text(
            student_answer
        )

        student_normalized = self._normalize_text(
            student_text
        )

        accepted_normalized = {
            self._normalize_text(value)
            for value in accepted_answers
            if str(value).strip()
        }

        is_correct = (
            bool(student_normalized)
            and student_normalized in accepted_normalized
        )

        # Also support 1-based option indexes such as 1, 2, 3, 4.
        if not is_correct:
            selected_option_text = self._resolve_selected_option_text(
                question=question,
                student_answer=student_text,
            )

            if selected_option_text:
                is_correct = (
                    self._normalize_text(
                        selected_option_text
                    )
                    in accepted_normalized
                )

        marks_awarded = (
            max_marks
            if is_correct
            else 0.0
        )

        return {
            "question_id": question.get("question_id"),
            "question": question.get("question", ""),
            "question_type": self._question_type(question),
            "student_answer": student_text,
            "expected_answer": accepted_answers,
            "marks_awarded": round(
                marks_awarded,
                2,
            ),
            "max_marks": round(
                max_marks,
                2,
            ),
            "status": (
                "correct"
                if is_correct
                else "wrong"
            ),
            "feedback": (
                "Correct answer."
                if is_correct
                else "Answer does not match the approved answer key."
            ),
            "confidence": student_answer.get("confidence"),
            "source_locator": student_answer.get(
                "source_locator"
            ),
            "review_required": False,
        }

    # ========================================================
    # SUBJECTIVE EVALUATION
    # ========================================================

    def _evaluate_subjective_question(
        self,
        *,
        question: dict[str, Any],
        student_answer: dict[str, Any],
        max_marks: float,
    ) -> dict[str, Any]:
        reference_answer = (
            question.get("reference_answer")
            or question.get("correct_answer")
            or question.get("expected_answer")
            or question.get("answer")
            or ""
        )

        rubric = (
            question.get("rubric")
            or question.get("marking_criteria")
            or question.get("marking_scheme")
            or ""
        )

        if not str(reference_answer).strip() and not str(rubric).strip():
            return {
                "question_id": question.get("question_id"),
                "question": question.get("question", ""),
                "question_type": self._question_type(question),
                "student_answer": self._answer_to_text(
                    student_answer
                ),
                "expected_answer": "",
                "marks_awarded": 0.0,
                "max_marks": round(
                    max_marks,
                    2,
                ),
                "status": "requires_review",
                "feedback": (
                    "No approved reference answer or marking rubric "
                    "was provided."
                ),
                "confidence": student_answer.get("confidence"),
                "source_locator": student_answer.get(
                    "source_locator"
                ),
                "review_required": True,
            }

        prompt = f"""
You are the Evaluation Agent of TCO.

Evaluate the student's answer against the APPROVED reference
answer and/or marking rubric.

Do not invent missing facts.
Do not use outside knowledge when the provided reference/rubric
is sufficient.
Do not award more than the maximum marks.
Be conservative when the answer is unclear.

QUESTION:
{question.get("question", "")}

MAX MARKS:
{max_marks}

STUDENT ANSWER:
{self._answer_to_text(student_answer)}

APPROVED REFERENCE ANSWER:
{reference_answer}

MARKING RUBRIC:
{rubric}

Return:
- marks_awarded
- correctness
- brief feedback
- important missing points
- whether teacher review is required
"""

        evaluation: SubjectiveEvaluation = self.model.invoke(
            prompt
        )

        marks_awarded = min(
            max(
                float(evaluation.marks_awarded),
                0.0,
            ),
            max_marks,
        )

        correctness = (
            evaluation.correctness
            or "unclear"
        ).strip().lower()

        if correctness not in {
            "correct",
            "partially_correct",
            "incorrect",
            "unclear",
        }:
            correctness = "unclear"

        review_required = bool(
            evaluation.review_required
            or correctness == "unclear"
        )

        return {
            "question_id": question.get("question_id"),
            "question": question.get("question", ""),
            "question_type": self._question_type(question),
            "student_answer": self._answer_to_text(
                student_answer
            ),
            "expected_answer": reference_answer,
            "marks_awarded": round(
                marks_awarded,
                2,
            ),
            "max_marks": round(
                max_marks,
                2,
            ),
            "status": correctness,
            "feedback": evaluation.feedback,
            "missing_points": evaluation.missing_points,
            "confidence": student_answer.get("confidence"),
            "source_locator": student_answer.get(
                "source_locator"
            ),
            "review_required": review_required,
        }

    # ========================================================
    # HELPERS
    # ========================================================

    @staticmethod
    def _question_type(
        question: dict[str, Any],
    ) -> str:
        return str(
            question.get("question_type")
            or question.get("type")
            or question.get("kind")
            or "subjective"
        ).strip().lower()

    @classmethod
    def _is_objective(
        cls,
        question_type: str,
        question: dict[str, Any],
    ) -> bool:
        objective_types = {
            "mcq",
            "multiple_choice",
            "multiple-choice",
            "choice",
            "single_choice",
            "single-choice",
            "true_false",
            "true-false",
            "boolean",
        }

        if question_type in objective_types:
            return True

        return bool(
            question.get("options")
            and (
                question.get("correct_option") is not None
                or question.get("correct_answer") is not None
                or question.get("accepted_answers")
            )
        )

    @staticmethod
    def _question_marks(
        question: dict[str, Any],
    ) -> float:
        value = (
            question.get("marks")
            if question.get("marks") is not None
            else question.get("points")
        )

        if value is None:
            value = question.get("max_marks")

        if value is None:
            return 0.0

        try:
            return max(
                float(value),
                0.0,
            )
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _accepted_answers(
        cls,
        question: dict[str, Any],
    ) -> list[str]:
        accepted = (
            question.get("accepted_answers")
            or question.get("correct_answers")
            or question.get("correct_answer")
        )

        if accepted is None:
            accepted = []

        if not isinstance(accepted, list):
            accepted = [accepted]

        correct_option = question.get(
            "correct_option"
        )

        if correct_option is not None:
            options = question.get(
                "options",
                [],
            )

            if isinstance(options, list):
                try:
                    option_index = int(
                        correct_option
                    ) - 1

                    if (
                        0 <= option_index
                        < len(options)
                    ):
                        accepted.append(
                            options[option_index]
                        )
                except (
                    TypeError,
                    ValueError,
                ):
                    # correct_option may already be option text.
                    accepted.append(
                        str(correct_option)
                    )

        return [
            str(value)
            for value in accepted
            if value is not None
        ]

    @classmethod
    def _resolve_selected_option_text(
        cls,
        *,
        question: dict[str, Any],
        student_answer: str,
    ) -> str | None:
        options = question.get("options", [])

        if not isinstance(options, list):
            return None

        value = str(student_answer).strip()

        try:
            option_index = int(value) - 1
        except (TypeError, ValueError):
            return None

        if (
            0 <= option_index
            < len(options)
        ):
            return str(
                options[option_index]
            )

        return None

    @staticmethod
    def _answer_to_text(
        student_answer: dict[str, Any],
    ) -> str:
        value = student_answer.get(
            "answer",
            "",
        )

        if isinstance(value, list):
            return " | ".join(
                str(item)
                for item in value
            )

        if value is None:
            return ""

        return str(value)

    @staticmethod
    def _normalize_text(
        value: Any,
    ) -> str:
        return " ".join(
            str(value)
            .strip()
            .lower()
            .split()
        )


# ============================================================
# BACKWARD-COMPATIBLE FUNCTION
# ============================================================


_default_agent: EvaluationAgent | None = None


def _get_default_evaluation_agent() -> EvaluationAgent:
    global _default_agent

    if _default_agent is None:
        _default_agent = EvaluationAgent()

    return _default_agent


def evaluation_agent(
    state: dict[str, Any],
) -> dict[str, Any]:
    return _get_default_evaluation_agent().run(
        state
    )
