from __future__ import annotations

from unittest.mock import patch

from backend.core.tool_result import ToolResult
from backend.rag import source_retrieval


class FakeDiscoveryService:
    called = False

    def __init__(self) -> None:
        FakeDiscoveryService.called = True

    def discover(self, state):
        return ToolResult.ok(
            data=[
                {
                    "title": "Python Classes",
                    "url": "https://example.com/python-classes",
                    "snippet": "Class documentation",
                    "source_type": "web",
                    "relevance_score": 0.9,
                    "domain": "example.com",
                    "approved": False,
                }
            ],
            metadata={"query": "python classes"},
        )


def test_web_mode_discovers_candidates_without_classroom() -> None:
    FakeDiscoveryService.called = False

    state = {
        "topic": "Python Classes",
        "teacher_id": "teacher-demo",
        "school_id": "TCO_TEST",
        "conversation_id": "conversation-1",
        "knowledge_source": "web_search",
        "source_preference": "web_search_only",
        "source_candidates": [],
    }

    with patch.object(source_retrieval, "SourceDiscoveryService", FakeDiscoveryService):
        result = source_retrieval.retrieve_source(state)

    assert FakeDiscoveryService.called is True
    assert result["knowledge_source"] == "web_search"
    assert result["source_status"] == "web_source_candidates_available"
    assert result["approval_required"] is True
    assert result["source_approved"] is False
    assert len(result["source_candidates"]) == 1
