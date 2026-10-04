from backend.core.source_policy import get_source_policy
from backend.core.tool_result import ToolResult
from backend.schemas.source import SourceCandidate
from backend.state import TCOState
from backend.tools.web_search import WebSearchTool


class SourceDiscoveryService:
    """
    Discovers candidate sources based on the teacher's request.

    This service DOES NOT:
        - approve sources
        - generate educational content
        - trust a source automatically
        - publish anything

    It only:
        1. Builds a search query.
        2. Applies source preferences.
        3. Calls the web search tool.
        4. Returns candidate sources.
    """

    def __init__(self):
        self.web_search = WebSearchTool()

    def discover(
        self,
        state: TCOState,
    ) -> ToolResult[list[SourceCandidate]]:
        """
        Discover candidate sources from the current TCO state.
        """

        # -----------------------------------------------------
        # Step 1: Build search query
        # -----------------------------------------------------

        query = self._build_query(state)

        if not query:
            return ToolResult.failure(
                error_code="SOURCE_DISCOVERY_QUERY_EMPTY",
                error_message=(
                    "Not enough information is available "
                    "to build a search query."
                ),
            )

        # -----------------------------------------------------
        # Step 2: Check requested source
        # -----------------------------------------------------

        requested_source = state.get("requested_source")

        policy = get_source_policy(
            requested_source
        )

        preferred_domains = None

        if policy:
            preferred_domains = list(
                policy.preferred_domains
            )

        # -----------------------------------------------------
        # Step 3: Call Web Search Tool
        # -----------------------------------------------------

        result = self.web_search.execute(
            query=query,
            max_results=5,
            include_domains=preferred_domains,
        )

        if not result.success:
            return result

        candidates = result.data or []

        # -----------------------------------------------------
        # Step 4: Ensure candidates are not approved
        # -----------------------------------------------------

        candidates = self._prepare_candidates(
            candidates
        )

        # -----------------------------------------------------
        # Step 5: Return structured result
        # -----------------------------------------------------

        return ToolResult.ok(
            data=candidates,
            metadata={
                "query": query,
                "requested_source": requested_source,
                "preferred_domains": (
                    preferred_domains or []
                ),
                "result_count": len(candidates),
            },
        )

    # =========================================================
    # QUERY BUILDER
    # =========================================================

    def _build_query(
        self,
        state: TCOState,
    ) -> str:
        """
        Build a search query from structured state.

        Example:

            class_level = 10
            subject = Science
            requested_source = NCERT

        Result:

            Class 10 Science NCERT
        """

        parts: list[str] = []

        class_level = state.get("class_level")
        subject = state.get("subject")
        chapter = state.get("chapter")
        topic = state.get("topic")
        requested_source = state.get(
            "requested_source"
        )

        if class_level:
            parts.append(
                f"Class {class_level}"
            )

        if subject:
            parts.append(
                str(subject)
            )

        if chapter:
            parts.append(
                str(chapter)
            )

        if topic:
            # Avoid repeating subject/chapter
            if topic not in parts:
                parts.append(
                    str(topic)
                )

        if requested_source:
            parts.append(
                str(requested_source)
            )

        # If structured fields are not sufficient,
        # fall back to the original teacher request.
        if not parts:

            teacher_request = state.get(
                "teacher_request",
                "",
            ).strip()

            return teacher_request[:500]

        return " ".join(parts).strip()

    # =========================================================
    # CANDIDATE PREPARATION
    # =========================================================

    def _prepare_candidates(
        self,
        candidates: list[SourceCandidate],
    ) -> list[SourceCandidate]:
        """
        Prepare candidate sources for teacher review.

        Every candidate remains unapproved.

        Search success does NOT equal source approval.
        """

        prepared: list[SourceCandidate] = []

        for candidate in candidates:

            candidate = candidate.model_copy(
                update={
                    "approved": False,
                }
            )

            prepared.append(candidate)

        return prepared


# =============================================================
# CONVENIENCE FUNCTION
# =============================================================

def discover_sources(
    state: TCOState,
) -> ToolResult[list[SourceCandidate]]:
    """
    Convenience wrapper used by workflows.

    Instead of:

        service = SourceDiscoveryService()
        result = service.discover(state)

    we can simply use:

        result = discover_sources(state)
    """

    service = SourceDiscoveryService()

    return service.discover(state)