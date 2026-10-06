from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from backend.core.base_agent import BaseAgent
from backend.core.model_provider import get_chat_model
from backend.services.analytics_service import AnalyticsService
from backend.state import TCOState


class AnalyticsRequest(BaseModel):
    operation: str = Field(
        description=(
            "One of: filter_students, student_detail, "
            "assessment_performance, class_performance, ranking."
        )
    )
    student_name: str | None = None
    topic: str | None = None
    subject: str | None = None
    class_level: str | None = None
    section: str | None = None
    school_id: str | None = None
    assessment_id: int | None = None
    min_marks: float | None = None
    max_marks: float | None = None
    min_percentage: float | None = None
    max_percentage: float | None = None
    limit: int = 10
    descending: bool = True
    request_scope: str = "class"


ANALYTICS_AGENT_PROMPT = """
You are the Analytics Agent of TCO (Teacher Co-Worker).

Your job is to understand a teacher's natural-language analytics request
and convert it into a structured analytics operation.

Allowed operations:
- filter_students
- student_detail
- assessment_performance
- class_performance
- ranking

Examples:
"mujhe 20 marks se less students dikhao"
    -> filter_students
    -> max_marks=20

"20 marks se kam students dikhao"
    -> filter_students
    -> max_marks=20

"less than 20 marks students dikhao"
    -> filter_students
    -> max_marks=20

"60% se kam students dikhao"
    -> filter_students
    -> max_percentage=60

"10 marks se zyada students dikhao"
    -> filter_students
    -> min_marks=10

"10 marks se more students dikhao"
    -> filter_students
    -> min_marks=10

"top students dikhao"
    -> ranking
    -> descending=true

"bottom students dikhao"
    -> ranking
    -> descending=false

"electro ki detail dikhao"
    -> student_detail
    -> student_name="electro"

"class performance dikhao"
    -> class_performance

Rules:
- Never invent student IDs.
- Never invent assessment IDs.
- Never invent numeric filters.
- Preserve values explicitly present in the teacher request.
- A student-detail request does not require subject/topic/class unless the
  teacher explicitly provides one.
- Do not write SQL.
- Do not access SQLite directly.
- Do not modify the database.
- Do not send email.
- Do not generate charts. The Analytics Service prepares
  visualization-ready data.
"""


class AnalyticsAgent(BaseAgent):
    name = "analytics_agent"

    description = (
        "Interprets teacher analytics requests and delegates deterministic "
        "performance analysis to AnalyticsService."
    )

    capabilities = ("analytics.performance",)

    def __init__(
        self,
        model: Any | None = None,
        service: AnalyticsService | None = None,
    ) -> None:
        self.service = service or AnalyticsService()

        self.model = (
            model
            if model is not None
            else get_chat_model().with_structured_output(
                AnalyticsRequest
            )
        )

    @staticmethod
    def _apply_deterministic_filter_overrides(
        teacher_request: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Correct directional numeric filters from natural-language
        phrases before execution.

        Examples:
            "20 marks se less" -> max_marks=20
            "20 marks se kam" -> max_marks=20
            "10 marks se zyada" -> min_marks=10
            "60% se kam" -> max_percentage=60
            "70% se zyada" -> min_percentage=70

        Only values explicitly present in the teacher request are used.
        """

        text = teacher_request.lower().strip()

        # ---------------------------------------------------------
        # MARKS: LESS THAN / BELOW / KAM
        # ---------------------------------------------------------

        less_marks_patterns = [
            r"(\d+(?:\.\d+)?)\s*marks?\s*(?:se\s*)?(?:less|kam|below)",
            r"(?:less|below)\s*(?:than)?\s*(\d+(?:\.\d+)?)\s*marks?",
            r"(\d+(?:\.\d+)?)\s*(?:marks?)?\s*(?:se\s*)?(?:kam|less)",
        ]

        for pattern in less_marks_patterns:
            match = re.search(pattern, text)

            if match:
                value = float(match.group(1))
                data["max_marks"] = value
                data["min_marks"] = None
                break

        # ---------------------------------------------------------
        # MARKS: MORE THAN / ABOVE / ZYADA
        # ---------------------------------------------------------

        more_marks_patterns = [
            r"(\d+(?:\.\d+)?)\s*marks?\s*(?:se\s*)?(?:more|zyada|above)",
            r"(?:more|above)\s*(?:than)?\s*(\d+(?:\.\d+)?)\s*marks?",
            r"(\d+(?:\.\d+)?)\s*(?:marks?)?\s*(?:se\s*)?(?:zyada|more)",
        ]

        for pattern in more_marks_patterns:
            match = re.search(pattern, text)

            if match:
                value = float(match.group(1))
                data["min_marks"] = value
                data["max_marks"] = None
                break

        # ---------------------------------------------------------
        # PERCENTAGE: LESS THAN / BELOW / KAM
        # ---------------------------------------------------------

        less_percentage_patterns = [
            r"(\d+(?:\.\d+)?)\s*%\s*(?:se\s*)?(?:less|kam|below)",
            r"(?:less|below)\s*(?:than)?\s*(\d+(?:\.\d+)?)\s*%",
            r"(\d+(?:\.\d+)?)\s*(?:percent|percentage)\s*(?:se\s*)?(?:kam|less)",
        ]

        for pattern in less_percentage_patterns:
            match = re.search(pattern, text)

            if match:
                value = float(match.group(1))
                data["max_percentage"] = value
                data["min_percentage"] = None
                break

        # ---------------------------------------------------------
        # PERCENTAGE: MORE THAN / ABOVE / ZYADA
        # ---------------------------------------------------------

        more_percentage_patterns = [
            r"(\d+(?:\.\d+)?)\s*%\s*(?:se\s*)?(?:more|zyada|above)",
            r"(?:more|above)\s*(?:than)?\s*(\d+(?:\.\d+)?)\s*%",
            r"(\d+(?:\.\d+)?)\s*(?:percent|percentage)\s*(?:se\s*)?(?:zyada|more)",
        ]

        for pattern in more_percentage_patterns:
            match = re.search(pattern, text)

            if match:
                value = float(match.group(1))
                data["min_percentage"] = value
                data["max_percentage"] = None
                break

        return data

    def _resolve_request(
        self,
        state: TCOState,
        task: Any | None,
    ) -> AnalyticsRequest:
        task_input = getattr(task, "input_data", {}) or {}

        teacher_request = str(
            task_input.get(
                "teacher_request",
                state.get("teacher_request", ""),
            )
            or ""
        ).strip()

        if not teacher_request:
            raise ValueError(
                "Teacher analytics request is empty."
            )

        prompt = f"""
{ANALYTICS_AGENT_PROMPT}

TEACHER REQUEST:
{teacher_request}

EXPLICIT STATE CONTEXT:
school_id = {state.get("school_id", "")}
student_name = {state.get("student_name", "")}
topic = {state.get("topic", "")}
subject = {state.get("subject", "")}
class_level = {state.get("class_level", "")}
section = {state.get("section", "")}
assessment_id = {state.get("assessment_id", "")}
"""

        request: AnalyticsRequest = self.model.invoke(prompt)

        # Explicit model result first.
        data = request.model_dump()

        # ---------------------------------------------------------
        # Explicit context from state/task is authoritative.
        # ---------------------------------------------------------

        for key in (
            "student_name",
            "topic",
            "subject",
            "class_level",
            "section",
            "school_id",
            "assessment_id",
        ):
            state_value = (
                state.get(key)
                if key in state
                else task_input.get(key)
            )

            if state_value not in (None, ""):
                if key != "student_name" or not data.get(key):
                    data[key] = state_value

        # ---------------------------------------------------------
        # School context always wins.
        # ---------------------------------------------------------

        school_id = (
            state.get("school_id")
            or task_input.get("school_id")
            or data.get("school_id")
        )

        if school_id:
            data["school_id"] = school_id

        # ---------------------------------------------------------
        # Deterministically correct explicit natural-language
        # directional filters.
        # ---------------------------------------------------------

        data = self._apply_deterministic_filter_overrides(
            teacher_request,
            data,
        )

        return AnalyticsRequest.model_validate(data)

    def _execute(
        self,
        request: AnalyticsRequest,
    ) -> tuple[Any, dict[str, Any]]:
        common = {
            "school_id": request.school_id,
            "class_level": request.class_level,
            "section": request.section,
            "subject": request.subject,
            "topic": request.topic,
            "assessment_id": request.assessment_id,
            "limit": max(1, request.limit),
        }

        # =========================================================
        # FILTER STUDENTS
        # =========================================================

        if request.operation == "filter_students":
            result = self.service.filter_students(
                student_name=request.student_name,
                min_marks=request.min_marks,
                max_marks=request.max_marks,
                min_percentage=request.min_percentage,
                max_percentage=request.max_percentage,
                **{
                    key: value
                    for key, value in common.items()
                    if key not in {"assessment_id", "limit"}
                },
                limit=max(1, request.limit),
            )

            return result, {}

        # =========================================================
        # STUDENT DETAIL
        # =========================================================

        if request.operation == "student_detail":
            if not request.student_name:
                raise ValueError(
                    "Please provide the student name for student detail."
                )

            result = self.service.get_student_detail(
                student_name=request.student_name,
                school_id=request.school_id,
                limit=max(1, request.limit),
            )

            visualization = {
                "student_performance": [
                    {
                        "student_name": row.get(
                            "student_name",
                            "",
                        ),
                        "percentage": row.get(
                            "percentage",
                            0.0,
                        ),
                    }
                    for row in result.get("results", [])
                ],
                "score_distribution": [],
                "summary": result.get(
                    "summary",
                    {},
                ),
            }

            return result, visualization

        # =========================================================
        # ASSESSMENT PERFORMANCE
        # =========================================================

        if request.operation == "assessment_performance":
            if request.assessment_id is None:
                raise ValueError(
                    "Please provide an assessment ID for assessment performance."
                )

            result = self.service.get_assessment_results(
                assessment_id=request.assessment_id,
                school_id=request.school_id,
                limit=max(1, request.limit),
            )

            return result, {
                "student_performance": [
                    {
                        "student_name": row.get(
                            "student_name",
                            "",
                        ),
                        "percentage": row.get(
                            "percentage",
                            0.0,
                        ),
                    }
                    for row in result
                ],
                "score_distribution": [],
                "summary": {},
            }

        # =========================================================
        # CLASS PERFORMANCE
        # =========================================================

        if request.operation == "class_performance":
            result = self.service.get_class_performance(
                **common
            )

            return result, AnalyticsService.build_visualization_data(
                result
            )

        # =========================================================
        # RANKING
        # =========================================================

        if request.operation == "ranking":
            ranking_common = {
                key: value
                for key, value in common.items()
                if key != "limit"
            }

            result = self.service.get_ranked_students(
                **ranking_common,
                limit=max(1, request.limit),
                descending=request.descending,
            )

            return result, {
                "student_performance": [
                    {
                        "student_name": row.get(
                            "student_name",
                            "",
                        ),
                        "percentage": row.get(
                            "percentage",
                            0.0,
                        ),
                    }
                    for row in result
                ],
                "score_distribution": [],
                "summary": {},
            }

        raise ValueError(
            f"Unsupported analytics operation: {request.operation}"
        )

    def run(
        self,
        state: TCOState,
        task: Any | None = None,
    ) -> TCOState:
        try:
            request = self._resolve_request(
                state,
                task,
            )

            result, visualization = self._execute(
                request
            )

            return {
                **state,
                "intent": "analytics",
                "required_capability": "analytics.performance",
                "analytics_request": request.model_dump(),
                "analytics_result": result,
                "analytics_visualization_data": visualization,
                "status": "analytics_completed",
                "error_code": None,
                "error_message": None,
            }

        except Exception as exc:
            return {
                **state,
                "intent": "analytics",
                "required_capability": "analytics.performance",
                "status": "analytics_failed",
                "error_code": "ANALYTICS_AGENT_FAILED",
                "error_message": str(exc),
            }