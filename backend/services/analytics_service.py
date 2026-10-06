from __future__ import annotations

from statistics import median
from typing import Any

from backend.services.result_store import ResultStore


class AnalyticsServiceError(RuntimeError):
    """Raised when analytics data cannot be computed."""


class AnalyticsService:
    """
    Deterministic analytics layer over ResultStore.

    The service owns database/result querying and metric calculation.
    The Analytics Agent only interprets the teacher request and delegates
    the concrete operation here.
    """

    PASS_PERCENTAGE = 40.0

    def __init__(self, result_store: ResultStore | None = None) -> None:
        self.result_store = result_store or ResultStore()

    def get_student_detail(
        self,
        *,
        student_name: str,
        school_id: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        if not student_name.strip():
            raise AnalyticsServiceError(
                "student_name is required for student_detail."
            )

        results = self.result_store.get_student_results(
            student_name=student_name.strip(),
            limit=max(1, limit),
        )

        if school_id:
            results = [
                row
                for row in results
                if str(row.get("student_school_id", "")) == school_id
            ]

        results = results[: max(1, limit)]

        if not results:
            return {
                "student_name": student_name.strip(),
                "student_email": "",
                "found": False,
                "result_count": 0,
                "summary": {},
                "results": [],
            }

        percentages = [
            float(row.get("percentage", 0.0))
            for row in results
            if row.get("percentage") is not None
        ]
        marks = [
            float(row.get("obtained_marks", 0.0))
            for row in results
            if row.get("obtained_marks") is not None
        ]

        latest = results[0]

        return {
            "student_name": latest.get("student_name") or student_name.strip(),
            "student_email": latest.get("student_email") or "",
            "found": True,
            "result_count": len(results),
            "summary": {
                "latest_marks": latest.get("obtained_marks"),
                "latest_total_marks": latest.get("total_marks"),
                "latest_percentage": latest.get("percentage"),
                "average_percentage": (
                    round(sum(percentages) / len(percentages), 2)
                    if percentages
                    else None
                ),
                "highest_percentage": max(percentages) if percentages else None,
                "lowest_percentage": min(percentages) if percentages else None,
                "average_marks": (
                    round(sum(marks) / len(marks), 2)
                    if marks
                    else None
                ),
            },
            "results": results,
        }

    def filter_students(
        self,
        *,
        school_id: str | None = None,
        class_level: str | None = None,
        section: str | None = None,
        student_name: str | None = None,
        subject: str | None = None,
        topic: str | None = None,
        assessment_id: int | None = None,
        min_marks: float | None = None,
        max_marks: float | None = None,
        min_percentage: float | None = None,
        max_percentage: float | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return self.result_store.query_results(
            student_name=student_name,
            topic=topic,
            subject=subject,
            class_level=class_level,
            section=section,
            school_id=school_id,
            min_marks=min_marks,
            max_marks=max_marks,
            min_percentage=min_percentage,
            max_percentage=max_percentage,
            limit=max(1, limit),
        )

    def get_assessment_results(
        self,
        *,
        assessment_id: int | None = None,
        school_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        rows = self.result_store.query_results(
            school_id=school_id,
            limit=max(1, limit),
        )

        if assessment_id is not None:
            rows = [
                row
                for row in rows
                if row.get("assessment_id") == assessment_id
            ]

        return rows[: max(1, limit)]

    def get_class_performance(
        self,
        *,
        school_id: str | None = None,
        class_level: str | None = None,
        section: str | None = None,
        subject: str | None = None,
        topic: str | None = None,
        assessment_id: int | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        rows = self.get_assessment_results(
            assessment_id=assessment_id,
            school_id=school_id,
            limit=max(1, limit),
        )

        if class_level:
            rows = [
                row
                for row in rows
                if str(row.get("student_class_level", "")) == class_level
            ]

        if section:
            rows = [
                row
                for row in rows
                if str(row.get("student_section", "")) == section
            ]

        if subject:
            rows = [
                row
                for row in rows
                if str(row.get("subject", "")) == subject
            ]

        if topic:
            rows = [
                row
                for row in rows
                if str(row.get("topic", "")) == topic
            ]

        if not rows:
            return {
                "found": False,
                "student_count": 0,
                "summary": {},
                "students": [],
                "score_distribution": {
                    "0-20": 0,
                    "21-40": 0,
                    "41-60": 0,
                    "61-80": 0,
                    "81-100": 0,
                },
            }

        percentages = [
            float(row.get("percentage", 0.0))
            for row in rows
            if row.get("percentage") is not None
        ]

        marks = [
            float(row.get("obtained_marks", 0.0))
            for row in rows
            if row.get("obtained_marks") is not None
        ]

        total_marks = [
            float(row.get("total_marks", 0.0))
            for row in rows
            if row.get("total_marks") is not None
        ]

        correct = sum(
            int(row.get("correct_answers") or 0)
            for row in rows
        )
        wrong = sum(
            int(row.get("wrong_answers") or 0)
            for row in rows
        )
        unanswered = sum(
            int(row.get("unanswered") or 0)
            for row in rows
        )

        passed = sum(
            1
            for value in percentages
            if value >= self.PASS_PERCENTAGE
        )

        distribution = {
            "0-20": 0,
            "21-40": 0,
            "41-60": 0,
            "61-80": 0,
            "81-100": 0,
        }

        for value in percentages:
            if value <= 20:
                distribution["0-20"] += 1
            elif value <= 40:
                distribution["21-40"] += 1
            elif value <= 60:
                distribution["41-60"] += 1
            elif value <= 80:
                distribution["61-80"] += 1
            else:
                distribution["81-100"] += 1

        student_rows = sorted(
            [
                {
                    "student_name": row.get("student_name", ""),
                    "percentage": float(row.get("percentage", 0.0)),
                    "obtained_marks": row.get("obtained_marks"),
                    "total_marks": row.get("total_marks"),
                }
                for row in rows
            ],
            key=lambda item: item["percentage"],
            reverse=True,
        )

        return {
            "found": True,
            "student_count": len(rows),
            "summary": {
                "average_percentage": (
                    round(sum(percentages) / len(percentages), 2)
                    if percentages
                    else None
                ),
                "median_percentage": (
                    median(percentages)
                    if percentages
                    else None
                ),
                "highest_percentage": (
                    max(percentages)
                    if percentages
                    else None
                ),
                "lowest_percentage": (
                    min(percentages)
                    if percentages
                    else None
                ),
                "average_marks": (
                    round(sum(marks) / len(marks), 2)
                    if marks
                    else None
                ),
                "total_marks": (
                    max(total_marks)
                    if total_marks
                    else None
                ),
                "pass_count": passed,
                "pass_rate": (
                    round((passed / len(rows)) * 100, 2)
                    if rows
                    else 0.0
                ),
                "total_correct_answers": correct,
                "total_wrong_answers": wrong,
                "total_unanswered": unanswered,
            },
            "students": rows,
            "score_distribution": distribution,
        }

    def get_ranked_students(
        self,
        *,
        school_id: str | None = None,
        class_level: str | None = None,
        section: str | None = None,
        subject: str | None = None,
        topic: str | None = None,
        assessment_id: int | None = None,
        limit: int = 10,
        descending: bool = True,
    ) -> list[dict[str, Any]]:
        rows = self.get_class_performance(
            school_id=school_id,
            class_level=class_level,
            section=section,
            subject=subject,
            topic=topic,
            assessment_id=assessment_id,
            limit=max(1, limit * 10),
        ).get("students", [])

        rows = sorted(
            rows,
            key=lambda item: float(item.get("percentage", 0.0)),
            reverse=descending,
        )

        return [
            {
                "rank": index,
                **row,
            }
            for index, row in enumerate(
                rows[: max(1, limit)],
                start=1,
            )
        ]

    @staticmethod
    def build_visualization_data(
        class_performance: dict[str, Any],
    ) -> dict[str, Any]:
        students = class_performance.get("students", []) or []
        distribution = (
            class_performance.get("score_distribution", {})
            or {}
        )

        return {
            "student_performance": [
                {
                    "student_name": row.get("student_name", ""),
                    "percentage": row.get("percentage", 0.0),
                }
                for row in students
            ],
            "score_distribution": [
                {
                    "range": label,
                    "students": count,
                }
                for label, count in distribution.items()
            ],
            "summary": class_performance.get("summary", {}) or {},
        }
