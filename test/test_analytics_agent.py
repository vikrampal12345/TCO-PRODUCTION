from __future__ import annotations

from backend.agents.analytics_agent import AnalyticsAgent
from backend.services.analytics_service import AnalyticsService


class FakeAnalyticsModel:
    def __init__(self, request: dict):
        self.request = request

    def invoke(self, prompt: str):
        from backend.agents.analytics_agent import AnalyticsRequest
        return AnalyticsRequest.model_validate(self.request)


class FakeAnalyticsService:
    def filter_students(self, **kwargs):
        return [
            {
                "student_name": "Rahul Sharma",
                "obtained_marks": 8.0,
                "total_marks": 20.0,
                "percentage": 40.0,
            }
        ]

    def get_student_detail(self, **kwargs):
        return {
            "student_name": "electro",
            "student_email": "electro@example.com",
            "found": True,
            "result_count": 1,
            "summary": {
                "latest_marks": 16.0,
                "latest_total_marks": 20.0,
                "latest_percentage": 80.0,
            },
            "results": [
                {
                    "student_name": "electro",
                    "percentage": 80.0,
                    "obtained_marks": 16.0,
                    "total_marks": 20.0,
                }
            ],
        }

    def get_assessment_results(self, **kwargs):
        return [
            {
                "student_name": "electro",
                "percentage": 80.0,
            }
        ]

    def get_class_performance(self, **kwargs):
        return {
            "found": True,
            "student_count": 1,
            "summary": {
                "average_percentage": 80.0,
            },
            "students": [
                {
                    "student_name": "electro",
                    "percentage": 80.0,
                }
            ],
            "score_distribution": {
                "0-20": 0,
                "21-40": 0,
                "41-60": 0,
                "61-80": 1,
                "81-100": 0,
            },
        }

    def get_ranked_students(self, **kwargs):
        return [
            {
                "rank": 1,
                "student_name": "electro",
                "percentage": 80.0,
            }
        ]


def run_case(request: dict, state: dict):
    agent = AnalyticsAgent(
        model=FakeAnalyticsModel(request),
        service=FakeAnalyticsService(),
    )
    result = agent.run(state)
    assert result["status"] == "analytics_completed"
    return result


def main() -> None:
    base_state = {
        "teacher_request": "analytics",
        "school_id": "TCO_TEST",
    }

    filtered = run_case(
        {
            "operation": "filter_students",
            "max_marks": 10,
            "limit": 10,
            "request_scope": "class",
        },
        base_state,
    )
    assert filtered["analytics_result"][0]["student_name"] == "Rahul Sharma"

    detail = run_case(
        {
            "operation": "student_detail",
            "student_name": "electro",
            "limit": 1,
            "request_scope": "student",
        },
        base_state,
    )
    assert detail["analytics_request"]["student_name"] == "electro"
    assert detail["analytics_result"]["found"] is True

    performance = run_case(
        {
            "operation": "class_performance",
            "limit": 10,
            "request_scope": "class",
        },
        base_state,
    )
    assert performance["analytics_result"]["student_count"] == 1
    assert "summary" in performance["analytics_visualization_data"]

    ranking = run_case(
        {
            "operation": "ranking",
            "limit": 10,
            "descending": True,
            "request_scope": "class",
        },
        base_state,
    )
    assert ranking["analytics_result"][0]["student_name"] == "electro"

    print("TCO ANALYTICS AGENT TEST PASSED")
    print("FILTER STUDENTS TEST PASSED")
    print("STUDENT DETAIL TEST PASSED")
    print("CLASS PERFORMANCE TEST PASSED")
    print("RANKING TEST PASSED")


if __name__ == "__main__":
    main()
