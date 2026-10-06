from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any

from tavily import TavilyClient

from backend.rag.vectorstore import index_documents


MAX_CONTENT_CHARACTERS = 750_000
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


class WebSourceIngestionError(Exception):
    """Raised when an approved web source cannot be fetched or indexed."""


class WebSourceIngestionService:
    """
    Fetch an explicitly teacher-approved web source with Tavily Extract,
    persist the extracted content, and index it through the common RAG
    pipeline.

    Contract used by the TCO Web Search + RAG flow:

        search
          -> teacher approval
          -> Tavily Extract
          -> markdown file
          -> Chroma indexing
          -> source-filtered RAG

    The service never treats a search candidate as approved automatically.
    """

    def __init__(self) -> None:
        api_key = os.getenv("TAVILY_API_KEY", "").strip()

        if not api_key:
            raise WebSourceIngestionError(
                "TAVILY_API_KEY environment variable is required."
            )

        self.client = TavilyClient(api_key=api_key)

    # =========================================================
    # HELPERS
    # =========================================================

    @staticmethod
    def _safe_filename(value: str) -> str:
        value = re.sub(
            r"[^A-Za-z0-9._-]+",
            "_",
            value.strip(),
        ).strip("._")

        return value[:120] or "web_source"

    @staticmethod
    def _extract_text_from_result(
        result: Any,
        selected_url: str,
    ) -> str:
        """
        Normalize Tavily Extract responses.

        Tavily can return a result object whose body is exposed as
        `raw_content`. The previous implementation could reference
        `raw_content` before defining it. This method defines it explicitly
        and supports common response shapes without assuming one exact SDK
        response layout.
        """

        if result is None:
            return ""

        # Single result dict.
        if isinstance(result, dict):
            direct_keys = (
                "raw_content",
                "content",
                "text",
                "markdown",
            )

            for key in direct_keys:
                value = result.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

            # Standard Tavily Extract response:
            # {"results": [{"url": "...", "raw_content": "..."}]}
            results = result.get("results")

            if isinstance(results, list):
                matching = None
                first_valid = None

                for item in results:
                    if not isinstance(item, dict):
                        continue

                    raw_content = item.get("raw_content")
                    if not isinstance(raw_content, str):
                        raw_content = item.get("content")
                    if not isinstance(raw_content, str):
                        raw_content = item.get("text")

                    if not raw_content or not raw_content.strip():
                        continue

                    if first_valid is None:
                        first_valid = raw_content.strip()

                    item_url = str(
                        item.get("url", "") or ""
                    ).strip()

                    if item_url == selected_url:
                        matching = raw_content.strip()
                        break

                return matching or first_valid or ""

        # Some SDK wrappers may return a list directly.
        if isinstance(result, list):
            first_valid = None

            for item in result:
                text = WebSourceIngestionService._extract_text_from_result(
                    item,
                    selected_url,
                )

                if text:
                    if first_valid is None:
                        first_valid = text

                    # Prefer exact URL matches when the nested item contains
                    # one; recursive normalization handles common shapes.
                    if isinstance(item, dict):
                        item_url = str(
                            item.get("url", "") or ""
                        ).strip()
                        if item_url == selected_url:
                            return text

            return first_valid or ""

        # Last-resort normalization for SDK model objects.
        for attr in (
            "raw_content",
            "content",
            "text",
            "markdown",
        ):
            value = getattr(result, attr, None)
            if isinstance(value, str) and value.strip():
                return value.strip()

        return ""

    @staticmethod
    def _find_failed_results(result: Any) -> list[dict[str, Any]]:
        if not isinstance(result, dict):
            return []

        failed = result.get("failed_results")
        if isinstance(failed, list):
            return [
                item for item in failed
                if isinstance(item, dict)
            ]

        return []

    # =========================================================
    # PUBLIC API
    # =========================================================

    def ingest(
        self,
        state: dict[str, Any],
        *,
        selected_source: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Fetch and index the explicitly approved source.

        Returns:
            {
                "file_path": "...",
                "source_id": "...",
                "source_type": "web_source",
                "chunk_count": int,
                "source_url": "...",
                "title": "...",
                "domain": "...",
            }
        """

        if state.get("source_approved") is not True:
            raise WebSourceIngestionError(
                "Web source must be teacher-approved before ingestion."
            )

        if not isinstance(selected_source, dict):
            raise WebSourceIngestionError(
                "selected_source must be a dictionary."
            )

        selected_url = str(
            selected_source.get("url", "")
            or state.get("source_url", "")
            or ""
        ).strip()

        if not selected_url:
            raise WebSourceIngestionError(
                "Approved web source URL is missing."
            )

        candidates = state.get("source_candidates") or []

        # Keep the original source approval policy:
        # only a URL that came from the discovered candidate list can be used.
        candidate_urls = {
            str(item.get("url", "") or "").strip()
            for item in candidates
            if isinstance(item, dict)
        }

        if candidate_urls and selected_url not in candidate_urls:
            raise WebSourceIngestionError(
                "The approved URL was not present in the current "
                "web-source candidate list."
            )

        teacher_id = str(
            state.get("teacher_id", "") or ""
        ).strip()

        school_id = str(
            state.get("school_id", "") or ""
        ).strip()

        conversation_id = str(
            state.get("conversation_id", "") or ""
        ).strip()

        if not teacher_id:
            raise WebSourceIngestionError(
                "teacher_id is required."
            )

        if not school_id:
            raise WebSourceIngestionError(
                "school_id is required."
            )

        if not conversation_id:
            raise WebSourceIngestionError(
                "conversation_id is required."
            )

        title = str(
            selected_source.get("title", "")
            or "web_source"
        ).strip()

        domain = str(
            selected_source.get("domain", "")
            or ""
        ).strip()

        # Deterministic source id for the URL + isolation scope.
        url_hash = hashlib.sha256(
            selected_url.encode("utf-8")
        ).hexdigest()[:16]

        source_id = (
            f"web_teacher_{teacher_id}"
            f"_school_{school_id}"
            f"_conversation_{conversation_id}"
            f"_url_{url_hash}"
        )

        # -----------------------------------------------------
        # Reuse already-fetched content when available.
        # -----------------------------------------------------

        existing_path = str(
            state.get("web_source_content_path", "")
            or ""
        ).strip()

        existing_source_id = str(
            state.get("source", "")
            or ""
        ).strip()

        if (
            state.get("web_source_fetched") is True
            and existing_path
            and Path(existing_path).is_file()
            and existing_source_id
        ):
            return {
                "file_path": existing_path,
                "source_id": existing_source_id,
                "source_type": "web_source",
                "chunk_count": 0,
                "source_url": selected_url,
                "title": title,
                "domain": domain,
                "reused_existing_content": True,
            }

        # -----------------------------------------------------
        # Tavily Extract
        # -----------------------------------------------------

        try:
            extract_result = self.client.extract(
                urls=selected_url,
                extract_depth="advanced",
                format="markdown",
            )
        except Exception as exc:
            raise WebSourceIngestionError(
                f"Could not fetch approved web source: {exc}"
            ) from exc

        content = self._extract_text_from_result(
            extract_result,
            selected_url,
        )

        if not content:
            failed_results = self._find_failed_results(
                extract_result
            )

            detail = ""
            if failed_results:
                detail = str(
                    failed_results[0].get(
                        "error",
                        "",
                    )
                    or ""
                ).strip()

            if detail:
                raise WebSourceIngestionError(
                    "Tavily extracted no content from the approved source: "
                    f"{detail}"
                )

            raise WebSourceIngestionError(
                "Tavily extracted no readable content from the approved source."
            )

        content = content[:MAX_CONTENT_CHARACTERS].strip()

        if not content:
            raise WebSourceIngestionError(
                "Approved web source returned empty content."
            )

        # -----------------------------------------------------
        # Persist source content
        # -----------------------------------------------------

        target_dir = (
            Path("data")
            / "documents"
            / "web_sources"
            / conversation_id
        )

        target_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        safe_title = self._safe_filename(title)

        target_path = (
            target_dir
            / f"{url_hash}_{safe_title}.md"
        )

        target_path.write_text(
            content,
            encoding="utf-8",
        )

        # -----------------------------------------------------
        # Common RAG indexing
        #
        # IMPORTANT:
        # `source` is the exact content path used by
        # source-filtered retrieval.
        # -----------------------------------------------------

        metadata = {
            "source": str(target_path),
            "source_type": "web_source",
            "teacher_id": teacher_id,
            "school_id": school_id,
            "conversation_id": conversation_id,
            "file_name": target_path.name,
            "source_url": selected_url,
            "title": title,
            "domain": domain,
        }

        document = {
            "text": content,
            "metadata": metadata,
        }

        try:
            chunk_count = index_documents(
                [document],
                source_id=source_id,
                chunk_size=CHUNK_SIZE,
                chunk_overlap=CHUNK_OVERLAP,
            )
        except Exception as exc:
            raise WebSourceIngestionError(
                f"Could not index approved web source into RAG: {exc}"
            ) from exc

        return {
            "file_path": str(target_path),
            "source_id": source_id,
            "source_type": "web_source",
            "chunk_count": chunk_count,
            "source_url": selected_url,
            "title": title,
            "domain": domain,
            "reused_existing_content": False,
        }
