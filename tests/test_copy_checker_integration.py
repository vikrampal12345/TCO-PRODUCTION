from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.agents.copy_checking_agent import CopyCheckingAgent
from backend.copy_checker.services.marking_scheme_importer import (
    MarkingSchemeImportError,
    load_marking_scheme,
)
from backend.copy_checker.services.grading_runner import (
    _expected_question_numbers_from_scheme,
)


def test_locked_marking_scheme_txt_is_imported(tmp_path: Path) -> None:
    path = tmp_path / "marking_scheme.txt"
    path.write_text(
        """ASSESSMENT_ID: DEMO-001
STATUS: locked
MCQ: 1
SHORT_ANSWER: 2
TOTAL_MARKS: 3
Question_Number,Type,Correct_Answer
1,MCQ,B
2,Short_Answer,Reference answer for Q2
""",
        encoding="utf-8",
    )

    scheme = load_marking_scheme(path)

    assert scheme.assessment_id == "DEMO-001"
    assert scheme.status == "locked"
    assert scheme.total_marks == 3
    assert [q.question_no for q in scheme.questions] == [1, 2]
    assert scheme.questions[0].correct_answer == "B"
    assert scheme.questions[1].evaluation_guidance == "Reference answer for Q2"


def test_unlocked_marking_scheme_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "marking_scheme.txt"
    path.write_text(
        """ASSESSMENT_ID: DEMO-001
STATUS: proposed
MCQ: 1
SHORT_ANSWER: 2
Question_Number,Type,Correct_Answer
1,MCQ,B
""",
        encoding="utf-8",
    )

    with pytest.raises(MarkingSchemeImportError, match="locked"):
        load_marking_scheme(path)


def test_copy_checking_agent_asks_for_required_files() -> None:
    result = CopyCheckingAgent().run(state={}, task=None)

    assert result["status"] == "waiting_for_teacher"
    assert set(result["missing_information"]) == {
        "question_paper",
        "locked_marking_scheme",
        "student_answer_sheet_pdf",
    }


def test_unified_api_has_copy_checking_and_tco_routes() -> None:
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["service"] == "tco-unified-backend"

    paths = app.openapi()["paths"]
    assert "/api/v1/copy-checking/grade" in paths
    assert "/api/v1/copy-checking/jobs/{job_id}/checked-copy" in paths
    assert "/api/v1/tco/execute" in paths


def test_copy_checking_upload_contract_rejects_wrong_extensions() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/copy-checking/grade?pages=2",
        files={
            "question_paper": ("paper.pdf", b"not a text paper", "application/pdf"),
            "marking_scheme": ("scheme.txt", b"not a scheme", "text/plain"),
            "answer_copy": ("STU047.pdf", b"not a real PDF", "application/pdf"),
        },
    )
    assert response.status_code == 400
    assert "Question paper" in response.json()["detail"]


def test_copy_checking_page_limit_uses_configured_pdf_cap() -> None:
    from backend.copy_checker.core.config import settings

    client = TestClient(app)
    paths = app.openapi()["paths"]

    for route_path in (
        "/api/v1/copy-checking/grade",
        "/api/v1/copy-checking/orchestrated-grade",
    ):
        page_parameter = next(
            parameter
            for parameter in paths[route_path]["post"]["parameters"]
            if parameter["name"] == "pages"
        )
        assert page_parameter["schema"]["maximum"] == settings.max_pdf_pages

    response = client.post(
        f"/api/v1/copy-checking/grade?pages={settings.max_pdf_pages + 1}",
        files={
            "question_paper": ("paper.txt", b"Question paper", "text/plain"),
            "marking_scheme": ("scheme.txt", b"Marking scheme", "text/plain"),
            "answer_copy": ("STU047.pdf", b"PDF bytes", "application/pdf"),
        },
    )
    assert response.status_code == 422


def test_copy_checking_agent_uses_tco_registry_and_executor() -> None:
    from backend.core.registry import ComponentRegistry
    from backend.core.task import Task, TaskStatus
    from backend.core.task_executor import TaskExecutor
    from backend.core.task_router import TaskRouter

    registry = ComponentRegistry()
    registry.register_agent(CopyCheckingAgent())
    task = Task(capability="copy_checking.grade", input_data={})
    provider, routed_task = TaskRouter(registry).route(task)

    result = TaskExecutor().execute(provider, routed_task, {})

    assert result["status"] == "waiting_for_teacher"
    assert result["next_action"] == "ask_teacher"
    assert result["current_task"].status == TaskStatus.COMPLETED

def _orchestrated_test_files():
    return {
        "question_paper": (
            "Question.txt",
            b"Question 1: Select the correct option.",
            "text/plain",
        ),
        "marking_scheme": (
            "answerkey.txt",
            (
                b"ASSESSMENT_ID: TEST-ORCH-001\n"
                b"STATUS: locked\n"
                b"MCQ: 1\n"
                b"TOTAL_MARKS: 1\n"
                b"Question_Number,Type,Correct_Answer\n"
                b"1,MCQ,B\n"
            ),
            "text/plain",
        ),
        "answer_copy": (
            "Student_Orch.pdf",
            b"%PDF-1.4\nmock student answer sheet\n",
            "application/pdf",
        ),
    }


def test_orchestrated_copy_checking_route_is_exposed() -> None:
    paths = app.openapi()["paths"]

    route = "/api/v1/copy-checking/orchestrated-grade"
    assert route in paths
    assert "post" in paths[route]


def test_orchestrated_grade_runs_master_workflow_and_serves_pdf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import shutil
    from types import SimpleNamespace

    import backend.graph as graph_module

    client = TestClient(app)
    captured = {}

    def fake_invoke(initial_state: dict) -> dict:
        captured.update(initial_state)

        question_path = Path(initial_state["question_paper_path"])
        scheme_path = Path(initial_state["marking_scheme_path"])
        answer_path = Path(initial_state["answer_sheet_path"])

        assert question_path.is_file()
        assert scheme_path.is_file()
        assert answer_path.is_file()
        assert "STATUS: locked" in scheme_path.read_text(
            encoding="utf-8"
        )
        assert answer_path.read_bytes().startswith(b"%PDF-")
        assert initial_state["intent"] == "copy_checking"

        output_dir = Path(initial_state["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        job_id = initial_state["job_id"]
        checked_pdf = output_dir / f"{job_id}_checked.pdf"
        checked_pdf.write_bytes(b"%PDF-1.4\nmock checked copy\n")

        return {
            **initial_state,
            "status": "graded",
            "required_capability": "copy_checking.grade",
            "copy_checking_result": {
                "status": "success",
                "grading": {
                    "total_marks": 1.0,
                    "obtained_marks": 1.0,
                    "percentage": 100.0,
                },
            },
            "checked_copy_path": str(checked_pdf),
            "metadata": {
                **initial_state.get("metadata", {}),
                "task_provider": "copy_checking_agent",
            },
        }

    monkeypatch.setattr(
        graph_module,
        "workflow",
        SimpleNamespace(invoke=fake_invoke),
    )

    try:
        response = client.post(
            "/api/v1/copy-checking/orchestrated-grade?pages=2",
            files=_orchestrated_test_files(),
        )

        assert response.status_code == 200, response.text
        payload = response.json()

        assert payload["status"] == "success"
        assert payload["job_id"].startswith("CC-")
        assert payload["orchestration"]["entrypoint"] == (
            "master_agent_workflow"
        )
        assert payload["orchestration"]["required_capability"] == (
            "copy_checking.grade"
        )
        assert payload["orchestration"]["task_provider"] == (
            "copy_checking_agent"
        )

        checked_path = Path(payload["checked_copy_path"]).resolve()
        expected_output_dir = Path(captured["output_dir"]).resolve()

        assert checked_path.is_relative_to(expected_output_dir)
        assert checked_path.is_file()
        assert captured["job_id"] == payload["job_id"]
        assert captured["page_limit"] == 2

        download = client.get(payload["checked_copy_url"])
        assert download.status_code == 200
        assert download.content.startswith(b"%PDF-")

    finally:
        if captured.get("output_dir"):
            shutil.rmtree(
                Path(captured["output_dir"]),
                ignore_errors=True,
            )


def test_orchestrated_grade_returns_review_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    import backend.graph as graph_module

    client = TestClient(app)

    def fake_invoke(initial_state: dict) -> dict:
        return {
            **initial_state,
            "status": "review_required",
            "grading_started": False,
            "clarification_message": (
                "Teacher review is required before grading."
            ),
            "copy_checking_error": (
                "Extraction requires teacher verification."
            ),
        }

    monkeypatch.setattr(
        graph_module,
        "workflow",
        SimpleNamespace(invoke=fake_invoke),
    )

    response = client.post(
        "/api/v1/copy-checking/orchestrated-grade?pages=2",
        files=_orchestrated_test_files(),
    )

    assert response.status_code == 409
    payload = response.json()
    assert payload["status"] == "review_required"
    assert payload["grading_started"] is False
    assert payload["job_id"].startswith("CC-")


def test_expected_question_numbers_come_from_locked_scheme(
    tmp_path: Path,
) -> None:
    scheme_path = tmp_path / "complete_scheme.txt"
    scheme_path.write_text(
        """ASSESSMENT_ID: TEST-EXPECTED-001
STATUS: locked
MCQ: 1
SHORT_ANSWER: 2
TOTAL_MARKS: 5
Question_Number,Type,Correct_Answer
21,MCQ,B
22,Short_Answer,Reference answer for Q22
35,Short_Answer,Reference answer for Q35
""",
        encoding="utf-8",
    )

    scheme = load_marking_scheme(scheme_path)

    assert _expected_question_numbers_from_scheme(scheme) == [21, 22, 35]

def test_orchestrated_review_persists_inputs_and_is_retrievable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from types import SimpleNamespace

    import backend.api.copy_checking_routes as routes_module
    import backend.graph as graph_module

    review_root = tmp_path / "reviews"
    monkeypatch.setattr(routes_module, "REVIEW_ROOT", review_root)

    def fake_invoke(initial_state: dict) -> dict:
        return {
            **initial_state,
            "status": "review_required",
            "grading_started": False,
            "clarification_message": (
                "Teacher review is required before grading."
            ),
            "copy_checking_error": (
                "Extraction requires teacher verification."
            ),
            "aggregated_submission": {
                "answers": [
                    {"question_no": 1, "answer": "B", "status": "EXTRACTED"}
                ],
                "missing_questions": [2],
                "review_required": True,
            },
        }

    monkeypatch.setattr(
        graph_module,
        "workflow",
        SimpleNamespace(invoke=fake_invoke),
    )

    client = TestClient(app)
    upload_files = _orchestrated_test_files()

    response = client.post(
        "/api/v1/copy-checking/orchestrated-grade?pages=2",
        files=upload_files,
    )

    assert response.status_code == 409, response.text
    payload = response.json()
    assert payload["status"] == "review_required"
    assert payload["grading_started"] is False

    job_id = payload["job_id"]
    case_dir = review_root / job_id
    record_path = case_dir / "review.json"

    assert record_path.is_file()

    review_response = client.get(
        f"/api/v1/copy-checking/jobs/{job_id}/review"
    )
    assert review_response.status_code == 200, review_response.text

    review = review_response.json()
    assert review["job_id"] == job_id
    assert review["status"] == "review_required"
    assert review["grading_started"] is False
    assert review["reason"] == "Extraction requires teacher verification."
    assert review["aggregated_submission"] == {
        "answers": [
            {"question_no": 1, "answer": "B", "status": "EXTRACTED"}
        ],
        "missing_questions": [2],
        "review_required": True,
    }

    retained = review["retained_inputs"]
    assert set(retained) == {
        "question_paper",
        "marking_scheme",
        "answer_copy",
    }

    for field, relative_path in retained.items():
        safe_relative_path = Path(relative_path.replace("\\", "/"))
        saved_file = (case_dir / safe_relative_path).resolve()

        assert saved_file.is_relative_to(case_dir.resolve())
        assert saved_file.is_file()
        assert saved_file.read_bytes() == upload_files[field][1]

    assert review["input_filenames"]["question_paper"] == "Question.txt"
    assert review["input_filenames"]["marking_scheme"] == "answerkey.txt"
    assert review["input_filenames"]["answer_copy"] == "Student_Orch.pdf"

    # Unknown question must be rejected without changing the saved record.
    invalid_update = client.put(
        f"/api/v1/copy-checking/jobs/{job_id}/review/answers",
        json={"answers": [{"question_no": 99, "answer": "Unexpected answer"}]},
    )
    assert invalid_update.status_code == 422

    update_response = client.put(
        f"/api/v1/copy-checking/jobs/{job_id}/review/answers",
        json={
            "answers": [
                {"question_no": 1, "answer": "Teacher-verified answer B"},
                {"question_no": 2, "answer": "Teacher-entered answer for Q2"},
            ]
        },
    )
    assert update_response.status_code == 200, update_response.text
    updated = update_response.json()
    assert updated["status"] == "answers_updated"
    assert updated["grading_started"] is False
    assert updated["ready_for_grading"] is False
    assert set(updated["updated_questions"]) == {1, 2}

    refreshed_response = client.get(
        f"/api/v1/copy-checking/jobs/{job_id}/review"
    )
    assert refreshed_response.status_code == 200
    refreshed = refreshed_response.json()
    corrected_by_number = {
        item["question_no"]: item
        for item in refreshed["aggregated_submission"]["answers"]
    }
    assert corrected_by_number[1]["answer"] == "Teacher-verified answer B"
    assert corrected_by_number[1]["status"] == "TEACHER_CORRECTED"
    assert corrected_by_number[2]["answer"] == "Teacher-entered answer for Q2"
    assert corrected_by_number[2]["status"] == "TEACHER_CORRECTED"
    assert refreshed["status"] == "review_required"
    assert refreshed["grading_started"] is False
    assert refreshed["ready_for_grading"] is False
    assert len(refreshed["teacher_corrections"]) == 2


def test_copy_checking_review_returns_404_for_unknown_job() -> None:
    client = TestClient(app)

    response = client.get(
        "/api/v1/copy-checking/jobs/CC-000000000000/review"
    )

    assert response.status_code == 404


def test_workflow_blocks_partial_copy_and_reports_actual_page_count() -> None:
    from backend.copy_checker.schemas.submission import AggregatedSubmission
    from backend.copy_checker.services.in_memory_grading_workflow import (
        InMemoryGradingWorkflow,
        SubmissionReviewRequired,
    )

    class FakeAggregationService:
        def aggregate(self, page_results, **kwargs):
            return AggregatedSubmission(
                job_id=kwargs.get("job_id"),
                student_number=kwargs.get("student_number"),
                total_pages=len(page_results),
                processed_pages=len(page_results),
                expected_questions=[1, 2],
                missing_questions=[2],
                review_required=False,
                warnings=[],
                metadata=dict(kwargs.get("metadata") or {}),
            )

    class NeverGrade:
        def grade_submission(self, **kwargs):
            raise AssertionError(
                "Grading must not run for an incompletely processed PDF."
            )

    workflow = InMemoryGradingWorkflow(
        page_count_fn=lambda pdf_path: 4,
        render_page_fn=lambda pdf_path, page_no: object(),
        extract_page_fn=lambda **kwargs: object(),
        aggregation_service=FakeAggregationService(),
        grading_model=NeverGrade(),
        max_pages=2,
    )

    with pytest.raises(SubmissionReviewRequired) as captured:
        workflow.run(
            pdf_path="simulated-four-page.pdf",
            marking_scheme=None,
            job_id="CC-123456abcdef",
            student_number="STU-TEST",
            expected_question_numbers=[1, 2],
        )

    submission = captured.value.submission

    assert submission.total_pages == 4
    assert submission.processed_pages == 2
    assert submission.review_required is True
    assert submission.metadata["actual_pdf_pages"] == 4
    assert submission.metadata["pages_processed"] == 2
    assert submission.metadata["partial_copy_processing"] is True
    assert any(
        "processed 2 of 4 PDF pages" in warning
        for warning in submission.warnings
    )


def test_complete_copy_still_requires_teacher_approval_before_grading() -> None:
    from backend.copy_checker.schemas.submission import AggregatedSubmission
    from backend.copy_checker.services.in_memory_grading_workflow import (
        InMemoryGradingWorkflow,
        SubmissionReviewRequired,
    )

    class FakeAggregationService:
        def aggregate(self, page_results, **kwargs):
            return AggregatedSubmission(
                job_id=kwargs.get("job_id"),
                student_number=kwargs.get("student_number"),
                total_pages=len(page_results),
                processed_pages=len(page_results),
                expected_questions=[1],
                missing_questions=[],
                review_required=False,
                warnings=[],
                metadata=dict(kwargs.get("metadata") or {}),
            )

    class NeverGrade:
        def grade_submission(self, **kwargs):
            raise AssertionError(
                "Grading must wait for explicit teacher approval."
            )

    workflow = InMemoryGradingWorkflow(
        page_count_fn=lambda pdf_path: 4,
        render_page_fn=lambda pdf_path, page_no: object(),
        extract_page_fn=lambda **kwargs: object(),
        aggregation_service=FakeAggregationService(),
        grading_model=NeverGrade(),
        max_pages=4,
    )

    with pytest.raises(SubmissionReviewRequired) as captured:
        workflow.run(
            pdf_path="simulated-complete-four-page.pdf",
            marking_scheme=None,
            job_id="CC-654321abcdef",
            student_number="STU-TEST",
            expected_question_numbers=[1],
            metadata={"teacher_approval_required": True},
        )

    submission = captured.value.submission

    assert submission.total_pages == 4
    assert submission.processed_pages == 4
    assert submission.review_required is True
    assert submission.metadata["partial_copy_processing"] is False
    assert any(
        "Teacher approval is required before grading."
        in warning
        for warning in submission.warnings
    )


def _make_teacher_approval_review_case(tmp_path, monkeypatch, submission):
    import json
    from backend.api import copy_checking_routes as routes

    job_id = "CC-abcdef123456"
    monkeypatch.setattr(routes, "REVIEW_ROOT", tmp_path)

    case_dir = tmp_path / job_id
    case_dir.mkdir(parents=True)
    record = {
        "job_id": job_id,
        "status": "review_required",
        "grading_started": False,
        "aggregated_submission": submission,
    }
    (case_dir / "review.json").write_text(
        json.dumps(record),
        encoding="utf-8",
    )
    payload = routes.TeacherApprovalRequest(
        teacher_name="Test Teacher",
        confirm_all_answers_reviewed=True,
        confirm_marking_scheme_locked=True,
    )
    return routes, job_id, payload


def test_teacher_approval_blocks_partial_copy(tmp_path, monkeypatch) -> None:
    import pytest
    from fastapi import HTTPException

    routes, job_id, payload = _make_teacher_approval_review_case(
        tmp_path,
        monkeypatch,
        {
            "total_pages": 4,
            "processed_pages": 3,
            "expected_questions": [1],
            "missing_questions": [],
            "repeated_questions": [],
            "conflicting_questions": [],
            "unresolved_items": 0,
            "answers": [
                {
                    "question_no": 1,
                    "answer": "test",
                    "review_required": False,
                    "status": "TEACHER_CORRECTED",
                }
            ],
            "review_required": True,
            "metadata": {"partial_copy_processing": True},
        },
    )

    with pytest.raises(HTTPException) as caught:
        routes.approve_and_grade_copy_checking(job_id, payload)

    assert caught.value.status_code == 409
    assert "full-copy" in str(caught.value.detail).lower()


def test_teacher_approval_blocks_unresolved_questions(
    tmp_path,
    monkeypatch,
) -> None:
    import pytest
    from fastapi import HTTPException

    routes, job_id, payload = _make_teacher_approval_review_case(
        tmp_path,
        monkeypatch,
        {
            "total_pages": 4,
            "processed_pages": 4,
            "expected_questions": [1, 2],
            "missing_questions": [2],
            "repeated_questions": [],
            "conflicting_questions": [],
            "unresolved_items": 1,
            "answers": [
                {
                    "question_no": 1,
                    "answer": "test",
                    "review_required": False,
                    "status": "TEACHER_CORRECTED",
                }
            ],
            "review_required": True,
            "metadata": {"partial_copy_processing": False},
        },
    )

    with pytest.raises(HTTPException) as caught:
        routes.approve_and_grade_copy_checking(job_id, payload)

    assert caught.value.status_code == 409
    assert "resolve" in str(caught.value.detail).lower()


def test_teacher_approval_grades_reviewed_submission_and_creates_pdf(
    tmp_path,
    monkeypatch,
) -> None:
    import json

    from backend.api import copy_checking_routes as routes
    from backend.copy_checker.services import grading_model as grading_model_module
    from backend.copy_checker.services import marking_scheme_importer
    from backend.copy_checker.services import checked_copy_renderer
    from backend.copy_checker.services import in_memory_page_processor

    job_id = "CC-abcdef123456"
    review_root = tmp_path / "reviews"
    output_root = tmp_path / "outputs"
    case_dir = review_root / job_id
    inputs_dir = case_dir / "inputs"
    inputs_dir.mkdir(parents=True)

    question_path = inputs_dir / "question_paper.txt"
    scheme_path = inputs_dir / "marking_scheme.txt"
    answer_path = inputs_dir / "answer_copy.pdf"

    question_path.write_text("Question 1", encoding="utf-8")
    scheme_path.write_text("Locked test scheme", encoding="utf-8")
    answer_path.write_bytes(b"fake PDF bytes for mocked processor")

    record = {
        "job_id": job_id,
        "status": "review_required",
        "grading_started": False,
        "student_number": "STU-TEST",
        "retained_inputs": {
            "question_paper": "inputs/question_paper.txt",
            "marking_scheme": "inputs/marking_scheme.txt",
            "answer_copy": "inputs/answer_copy.pdf",
        },
        "aggregated_submission": {
            "job_id": job_id,
            "student_number": "STU-TEST",
            "total_pages": 4,
            "processed_pages": 4,
            "answers": [
                {
                    "question_no": 1,
                    "answer": "Teacher-reviewed answer",
                    "confidence": None,
                    "observations": [],
                    "status": "TEACHER_CORRECTED",
                    "review_required": False,
                    "warning": None,
                }
            ],
            "expected_questions": [1],
            "missing_questions": [],
            "repeated_questions": [],
            "conflicting_questions": [],
            "unresolved_items": 0,
            "review_required": True,
            "warnings": [
                "Teacher approval is required before grading."
            ],
            "metadata": {
                "partial_copy_processing": False,
                "teacher_approval_required": True,
            },
        },
    }

    review_path = case_dir / "review.json"
    review_path.write_text(
        json.dumps(record),
        encoding="utf-8",
    )

    monkeypatch.setattr(routes, "REVIEW_ROOT", review_root)
    monkeypatch.setattr(routes, "OUTPUT_ROOT", output_root)

    class FakeQuestion:
        question_no = 1

    class FakeScheme:
        status = "locked"
        assessment_id = "ASSESSMENT-TEST"
        questions = [FakeQuestion()]

    class FakePageImage:
        def close(self):
            pass

    class FakeProcessor:
        def get_page_count(self, path):
            return 4

        def render_page(self, path, page_no):
            return FakePageImage()

    class FakeEvaluation:
        total_marks = 1.0
        obtained_marks = 1.0
        percentage = 100.0
        pages = [
            {
                "page_number": 1,
                "questions": [
                    {
                        "question_no": 1,
                        "marks_awarded": 1.0,
                        "max_marks": 1.0,
                        "reason": "Matches the reviewed scheme.",
                        "confidence": 1.0,
                    }
                ],
            }
        ]

        def model_dump(self):
            return {
                "job_id": job_id,
                "status": "completed",
                "total_marks": self.total_marks,
                "obtained_marks": self.obtained_marks,
                "percentage": self.percentage,
                "pages": self.pages,
            }

    captured = {}

    class FakeGradingModel:
        def grade_submission(
            self,
            submission,
            marking_scheme,
            **kwargs,
        ):
            captured["answer"] = submission.answers[0].answer
            captured["review_required"] = submission.review_required
            captured["scheme_status"] = marking_scheme.status
            captured["kwargs"] = kwargs
            return FakeEvaluation()

    class FakeRenderer:
        def render(
            self,
            *,
            page_images,
            evaluation_result,
            output_dir,
            file_name,
        ):
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            result = output_dir / file_name
            result.write_bytes(b"mock checked PDF")
            return result

    monkeypatch.setattr(
        marking_scheme_importer,
        "load_marking_scheme",
        lambda path: FakeScheme(),
    )
    monkeypatch.setattr(
        grading_model_module,
        "GradingModel",
        FakeGradingModel,
    )
    monkeypatch.setattr(
        in_memory_page_processor,
        "InMemoryPageProcessor",
        FakeProcessor,
    )
    monkeypatch.setattr(
        checked_copy_renderer,
        "CheckedCopyRenderer",
        FakeRenderer,
    )

    payload = routes.TeacherApprovalRequest(
        teacher_name="Test Teacher",
        confirm_all_answers_reviewed=True,
        confirm_marking_scheme_locked=True,
        confirmed_blank_questions=[],
    )

    response = routes.approve_and_grade_copy_checking(
        job_id,
        payload,
    )

    assert response["status"] == "success"
    assert response["job_id"] == job_id
    assert response["grading"]["obtained_marks"] == 1.0
    assert response["checked_copy_url"].endswith("/checked-copy")

    assert captured["answer"] == "Teacher-reviewed answer"
    assert captured["review_required"] is False
    assert captured["scheme_status"] == "locked"

    checked_file = output_root / job_id / f"{job_id}_checked.pdf"
    assert checked_file.is_file()
    assert checked_file.read_bytes() == b"mock checked PDF"

    saved_record = json.loads(review_path.read_text(encoding="utf-8"))
    assert saved_record["status"] == "success"
    assert saved_record["grading_started"] is True
    assert saved_record["approval"]["approved"] is True
    assert saved_record["approval"]["teacher_name"] == "Test Teacher"
    assert saved_record["grading_result"]["obtained_marks"] == 1.0


def test_teacher_corrections_clear_issue_flags_and_recompute_unresolved_count(
    tmp_path,
    monkeypatch,
) -> None:
    import json

    from backend.api import copy_checking_routes as routes

    job_id = "CC-a1b2c3d4e5f6"
    review_root = tmp_path / "reviews"
    case_dir = review_root / job_id
    case_dir.mkdir(parents=True)

    review_path = case_dir / "review.json"
    record = {
        "job_id": job_id,
        "status": "review_required",
        "grading_started": False,
        "aggregated_submission": {
            "total_pages": 4,
            "processed_pages": 4,
            "answers": [
                {
                    "question_no": 1,
                    "answer": "Unclear extracted answer",
                    "confidence": 0.3,
                    "observations": [],
                    "status": "REVIEW_REQUIRED",
                    "review_required": True,
                    "warning": "Conflicting observations",
                }
            ],
            "expected_questions": [1, 2],
            "missing_questions": [2],
            "conflicting_questions": [1],
            "repeated_questions": [1],
            "unresolved_items": 3,
            "review_required": True,
            "warnings": ["Extraction needs teacher review."],
            "metadata": {"partial_copy_processing": False},
        },
    }

    review_path.write_text(
        json.dumps(record),
        encoding="utf-8",
    )
    monkeypatch.setattr(routes, "REVIEW_ROOT", review_root)

    payload = routes.TeacherAnswerCorrectionsRequest(
        answers=[
            routes.TeacherAnswerCorrection(
                question_no=1,
                answer="Teacher-confirmed answer for Q1",
            ),
            routes.TeacherAnswerCorrection(
                question_no=2,
                answer="Teacher-entered answer for Q2",
            ),
        ]
    )

    response = routes.update_copy_checking_review_answers(
        job_id,
        payload,
    )

    assert response["status"] == "answers_updated"
    assert response["grading_started"] is False
    assert response["ready_for_grading"] is False

    saved = json.loads(review_path.read_text(encoding="utf-8"))
    submission = saved["aggregated_submission"]

    assert submission["missing_questions"] == []
    assert submission["conflicting_questions"] == []
    assert submission["repeated_questions"] == []
    assert submission["unresolved_items"] == 0

    answers = {
        int(item["question_no"]): item
        for item in submission["answers"]
    }
    assert answers[1]["answer"] == "Teacher-confirmed answer for Q1"
    assert answers[2]["answer"] == "Teacher-entered answer for Q2"
    assert answers[1]["status"] == "TEACHER_CORRECTED"
    assert answers[2]["status"] == "TEACHER_CORRECTED"

    assert submission["review_required"] is True
    assert saved["status"] == "review_required"
    assert saved["grading_started"] is False
    assert saved["ready_for_grading"] is False
    assert saved["validation"]["grading_resume_enabled"] is False
    assert saved["validation"]["outstanding_extraction_issues"][
        "unresolved_items"
    ] == 0
    assert saved["validation"]["outstanding_extraction_issues"][
        "answers_still_marked_for_review"
    ] == []
    assert len(saved["teacher_corrections"]) == 2

