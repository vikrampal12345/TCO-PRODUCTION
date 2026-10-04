import json
import os
from urllib import request
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse

from dotenv import load_dotenv

from backend.core.base_tool import BaseTool
from backend.core.tool_result import ToolResult
from backend.schemas.source import SourceCandidate


load_dotenv()


class WebSearchTool(BaseTool):
    """
    Web search tool used by TCO for source discovery.

    Important:
    - This tool only discovers candidate sources.
    - It does NOT decide whether a source is trusted.
    - It does NOT automatically approve a source.
    - It does NOT generate educational content.
    """

    name = "web_search"

    description = (
        "Search the web and return candidate sources relevant "
        "to the teacher's request."
    )

    def __init__(self):
        self.api_key = os.getenv("TAVILY_API_KEY")

        self.endpoint = "https://api.tavily.com/search"

        # Safety limits for prototype
        self.max_query_length = 500
        self.default_max_results = 5
        self.max_allowed_results = 10

    def execute(
        self,
        query: str,
        max_results: int = 5,
        include_domains: list[str] | None = None,
    ) -> ToolResult[list[SourceCandidate]]:

        # -----------------------------------------------------
        # Input validation
        # -----------------------------------------------------

        if not query or not query.strip():
            return ToolResult.failure(
                error_code="INVALID_QUERY",
                error_message="Search query cannot be empty.",
            )

        query = query.strip()

        if len(query) > self.max_query_length:
            return ToolResult.failure(
                error_code="QUERY_TOO_LONG",
                error_message=(
                    f"Search query exceeds the limit of "
                    f"{self.max_query_length} characters."
                ),
            )

        if not self.api_key:
            return ToolResult.failure(
                error_code="WEB_SEARCH_NOT_CONFIGURED",
                error_message=(
                    "TAVILY_API_KEY is not configured in the .env file."
                ),
            )

        # Clamp result count
        max_results = max(
            1,
            min(max_results, self.max_allowed_results),
        )

        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False,
        }

        # Optional domain restriction
        if include_domains:
            cleaned_domains = [
                self._normalize_domain(domain)
                for domain in include_domains
                if domain and domain.strip()
            ]

            cleaned_domains = [
                domain
                for domain in cleaned_domains
                if domain
            ]

            if cleaned_domains:
                payload["include_domains"] = cleaned_domains

        try:
            body = json.dumps(payload).encode("utf-8")

            req = request.Request(
                self.endpoint,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                method="POST",
            )

            with request.urlopen(req, timeout=20) as response:
                response_body = response.read().decode("utf-8")

            data = json.loads(response_body)

        except HTTPError as exc:
            return ToolResult.failure(
                error_code="WEB_SEARCH_HTTP_ERROR",
                error_message=(
                    f"Web search provider returned HTTP "
                    f"{exc.code}."
                ),
            )

        except URLError as exc:
            return ToolResult.failure(
                error_code="WEB_SEARCH_NETWORK_ERROR",
                error_message=(
                    f"Could not connect to the web search provider: "
                    f"{exc.reason}"
                ),
            )

        except json.JSONDecodeError:
            return ToolResult.failure(
                error_code="WEB_SEARCH_INVALID_RESPONSE",
                error_message=(
                    "Web search provider returned invalid JSON."
                ),
            )

        except Exception as exc:
            return ToolResult.failure(
                error_code="WEB_SEARCH_FAILED",
                error_message=str(exc),
            )

        # -----------------------------------------------------
        # Parse search results
        # -----------------------------------------------------

        raw_results = data.get("results", [])

        candidates: list[SourceCandidate] = []

        for item in raw_results:

            title = str(item.get("title", "")).strip()
            url = str(item.get("url", "")).strip()
            snippet = str(
                item.get("content", "")
            ).strip()

            if not title or not url:
                continue

            domain = self._extract_domain(url)

            score = item.get("score")

            try:
                score = float(score) if score is not None else None
            except (TypeError, ValueError):
                score = None

            candidates.append(
                SourceCandidate(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source_type="web",
                    relevance_score=score,
                    domain=domain,
                    approved=False,
                )
            )

        if not candidates:
            return ToolResult.failure(
                error_code="NO_SEARCH_RESULTS",
                error_message=(
                    "No candidate sources were found for the query."
                ),
                metadata={
                    "query": query,
                },
            )

        return ToolResult.ok(
            data=candidates,
            metadata={
                "query": query,
                "result_count": len(candidates),
            },
        )

    # ---------------------------------------------------------
    # Helper methods
    # ---------------------------------------------------------

    @staticmethod
    def _extract_domain(url: str) -> str:
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return ""

    @staticmethod
    def _normalize_domain(domain: str) -> str:
        domain = domain.strip().lower()

        domain = domain.replace("https://", "")
        domain = domain.replace("http://", "")

        domain = domain.split("/")[0]

        return domain