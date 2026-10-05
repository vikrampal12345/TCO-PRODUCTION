from __future__ import annotations

import json
from unittest.mock import patch

from backend.tools.web_search import WebSearchTool


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(
            {
                "results": [
                    {
                        "title": "Python Classes",
                        "url": "https://docs.python.org/3/tutorial/classes.html",
                        "content": "Python classes documentation.",
                        "score": 0.92,
                    }
                ]
            }
        ).encode("utf-8")


def test_web_search_returns_unapproved_candidates() -> None:
    tool = WebSearchTool()

    with patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"}, clear=False):
        tool.api_key = "test-key"
        with patch("backend.tools.web_search.request.urlopen", return_value=FakeResponse()):
            result = tool.execute("python classes")

    assert result.success is True
    assert len(result.data) == 1
    assert result.data[0].url.startswith("https://docs.python.org")
    assert result.data[0].approved is False
