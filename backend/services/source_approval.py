from typing import Any

from backend.core.tool_result import ToolResult
from backend.schemas.source import SourceCandidate
from backend.state import TCOState


class SourceApprovalService:
    """
    Handles source selection and teacher approval.

    Responsibilities:
        - Validate that the selected source exists
          in the current candidate list.
        - Mark the selected source as approved.
        - Prepare approval metadata.

    Does NOT:
        - search the web
        - fetch source content
        - generate educational content
    """

    def approve_source(
        self,
        state: TCOState,
        selected_url: str,
        teacher_id: str | None = None,
        approval_comment: str = "",
    ) -> ToolResult[dict[str, Any]]:
        """
        Approve one source from the discovered candidates.
        """

        # -----------------------------------------------------
        # 1. Validate selection
        # -----------------------------------------------------

        if not selected_url or not selected_url.strip():
            return ToolResult.failure(
                error_code="SOURCE_SELECTION_EMPTY",
                error_message=(
                    "No source was selected. "
                    "Please select one of the discovered sources."
                ),
            )

        selected_url = selected_url.strip()

        # -----------------------------------------------------
        # 2. Get discovered candidates
        # -----------------------------------------------------

        raw_candidates = state.get(
            "source_candidates",
            []
        )

        if not raw_candidates:
            return ToolResult.failure(
                error_code="NO_SOURCE_CANDIDATES",
                error_message=(
                    "There are no discovered source candidates "
                    "available for approval."
                ),
            )

        # -----------------------------------------------------
        # 3. Find exact candidate
        # -----------------------------------------------------

        selected_candidate = self._find_candidate(
            candidates=raw_candidates,
            selected_url=selected_url,
        )

        if selected_candidate is None:
            return ToolResult.failure(
                error_code="INVALID_SOURCE_SELECTION",
                error_message=(
                    "The selected source was not found in the "
                    "current candidate list."
                ),
            )

        # -----------------------------------------------------
        # 4. Create approved source
        # -----------------------------------------------------

        approved_source = {
            "title": selected_candidate.title,
            "url": selected_candidate.url,
            "snippet": selected_candidate.snippet,
            "source_type": selected_candidate.source_type,
            "relevance_score": selected_candidate.relevance_score,
            "domain": selected_candidate.domain,

            # Explicit human approval
            "approved": True,

            "approved_by": teacher_id,
            "approval_comment": approval_comment.strip(),
        }

        # -----------------------------------------------------
        # 5. Update all candidates
        # -----------------------------------------------------

        updated_candidates = []

        for raw_candidate in raw_candidates:

            candidate = self._to_candidate(
                raw_candidate
            )

            is_selected = (
                candidate.url.strip()
                == selected_url
            )

            updated_candidate = candidate.model_copy(
                update={
                    "approved": is_selected,
                }
            )

            updated_candidates.append(
                updated_candidate.model_dump()
            )

        # -----------------------------------------------------
        # 6. Return structured result
        # -----------------------------------------------------

        result_data = {
            "selected_source": approved_source,

            "source_candidates": updated_candidates,

            "source_approved": True,

            "source_status": "source_approved",

            "approval_required": False,

            "approval_type": "source",

            "approval_status": "approved",

            "approved_by": teacher_id or "",

            "approval_comment": approval_comment.strip(),

            # Important:
            # Source is approved, but has NOT been fetched yet.
            "next_action": "fetch_source",
        }

        return ToolResult.ok(
            data=result_data,
            metadata={
                "selected_url": selected_url,
                "approved_by": teacher_id,
            },
        )

    # =========================================================
    # FIND CANDIDATE
    # =========================================================

    def _find_candidate(
        self,
        candidates: list[Any],
        selected_url: str,
    ) -> SourceCandidate | None:
        """
        Find the exact selected URL in the candidate list.

        Only a source that was actually discovered by the
        current discovery process can be approved.
        """

        for raw_candidate in candidates:

            candidate = self._to_candidate(
                raw_candidate
            )

            if candidate.url.strip() == selected_url:
                return candidate

        return None

    # =========================================================
    # NORMALIZE CANDIDATE
    # =========================================================

    @staticmethod
    def _to_candidate(
        candidate: Any,
    ) -> SourceCandidate:
        """
        Convert a dictionary or SourceCandidate into
        a SourceCandidate object.
        """

        if isinstance(
            candidate,
            SourceCandidate,
        ):
            return candidate

        if isinstance(candidate, dict):
            return SourceCandidate.model_validate(
                candidate
            )

        raise TypeError(
            "Invalid source candidate type."
        )


# =============================================================
# CONVENIENCE FUNCTION
# =============================================================

def approve_source(
    state: TCOState,
    selected_url: str,
    teacher_id: str | None = None,
    approval_comment: str = "",
) -> ToolResult:
    """
    Simple wrapper around SourceApprovalService.
    """

    service = SourceApprovalService()

    return service.approve_source(
        state=state,
        selected_url=selected_url,
        teacher_id=teacher_id,
        approval_comment=approval_comment,
    )