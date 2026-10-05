from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from backend.services.web_source_ingestion import (
    WebSourceIngestionError,
    WebSourceIngestionService,
)


def _service(tmp_path: Path) -> WebSourceIngestionService:
    with patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"}, clear=False):
        return WebSourceIngestionService(storage_root=tmp_path / "web_sources")


def test_web_source_requires_teacher_approval(tmp_path: Path) -> None:
    service = _service(tmp_path)

    state = {
        "teacher_id": "teacher-demo",
        "school_id": "TCO_TEST",
        "conversation_id": "conversation-1",
        "source_candidates": [
            {"title": "Example", "url": "https://example.com"}
        ],
        "source_approved": False,
    }

    try:
        service.ingest(state)
    except WebSourceIngestionError as exc:
        assert "teacher-approved" in str(exc)
    else:
        raise AssertionError("Unapproved source unexpectedly fetched")


def test_source_id_is_deterministic(tmp_path: Path) -> None:
    service = _service(tmp_path)

    first = service._build_source_id(
        "teacher-demo",
        "TCO_TEST",
        "conversation-1",
        "https://example.com/topic",
    )
    second = service._build_source_id(
        "teacher-demo",
        "TCO_TEST",
        "conversation-1",
        "https://example.com/topic",
    )

    assert first == second
    assert first.startswith("web_teacher_teacher-demo_school_TCO_TEST_conversation_conversation-1_url_")
