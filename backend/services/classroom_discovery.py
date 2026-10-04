from __future__ import annotations

import re
from typing import Any

from backend.tools.classroom import (
    ClassroomTool,
    ClassroomToolError,
)


class ClassroomDiscoveryError(Exception):
    """Raised when Classroom material discovery fails."""


class ClassroomMaterialDiscoveryService:
    """
    Discover relevant Google Classroom materials.

    Discovery is metadata-level retrieval.

    It does NOT:
    - download files
    - create embeddings
    - query ChromaDB
    - generate answers

    It identifies likely source materials so the next layer
    can choose what to ingest/retrieve.
    """

    def __init__(
        self,
        classroom_tool: ClassroomTool | None = None,
    ) -> None:
        self.classroom = (
            classroom_tool
            or ClassroomTool()
        )

    # =========================================================
    # PUBLIC API
    # =========================================================

    def discover(
        self,
        *,
        course_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Discover relevant Classroom materials.

        Ranking is based on:
        - material title
        - attachment title
        - material description
        - attachment URL

        Supported attachments receive a small tie-breaking
        preference ONLY after actual query relevance exists.
        """
        course_id = course_id.strip()
        query = query.strip()

        self._validate(
            course_id=course_id,
            query=query,
            top_k=top_k,
        )

        try:
            materials = (
                self.classroom.list_course_materials(
                    course_id
                )
            )
        except ClassroomToolError as exc:
            raise ClassroomDiscoveryError(
                f"Could not load Classroom materials: {exc}"
            ) from exc

        query_terms = self._extract_terms(
            query
        )

        ranked: list[
            tuple[float, dict[str, Any]]
        ] = []

        for material in materials:
            score, matched_terms = (
                self._score_material(
                    material,
                    query_terms,
                )
            )

            # IMPORTANT:
            # A material must have at least one actual
            # query match. Merely having a supported PDF
            # must NEVER make it relevant.
            if score <= 0 or not matched_terms:
                continue

            result = self._build_result(
                material=material,
                score=score,
                matched_terms=matched_terms,
            )

            ranked.append(
                (
                    score,
                    result,
                )
            )

        ranked.sort(
            key=lambda item: (
                item[0],
                self._result_priority(
                    item[1]
                ),
            ),
            reverse=True,
        )

        return [
            result
            for _, result in ranked[:top_k]
        ]

    # =========================================================
    # SCORING
    # =========================================================

    def _score_material(
        self,
        material: dict[str, Any],
        query_terms: set[str],
    ) -> tuple[float, list[str]]:
        """
        Calculate metadata relevance score.

        Weighting:
            Material title       = 10
            Attachment title     = 8
            Description           = 4
            URL                   = 1

        Exact all-term title match receives an additional bonus.

        Supported-file preference is only added when there
        is already genuine query relevance.
        """
        title = self._normalize_text(
            material.get(
                "title",
                "",
            )
        )

        description = self._normalize_text(
            material.get(
                "description",
                "",
            )
        )

        attachment_titles: list[str] = []
        attachment_urls: list[str] = []

        for attachment in material.get(
            "materials",
            [],
        ):
            attachment_titles.append(
                self._normalize_text(
                    attachment.get(
                        "title",
                        "",
                    )
                )
            )

            attachment_urls.append(
                self._normalize_text(
                    attachment.get(
                        "url",
                        "",
                    )
                )
            )

        attachment_title_text = " ".join(
            attachment_titles
        )

        description_text = " ".join(
            description.split()
        )

        url_text = " ".join(
            attachment_urls
        )

        score = 0.0
        matched_terms: set[str] = set()

        # -----------------------------------------------------
        # Query term matching
        # -----------------------------------------------------

        for term in query_terms:

            # Material title
            if self._term_matches(
                term,
                title,
            ):
                score += 10.0
                matched_terms.add(term)

            # Attachment titles
            if self._term_matches(
                term,
                attachment_title_text,
            ):
                score += 8.0
                matched_terms.add(term)

            # Description
            if self._term_matches(
                term,
                description_text,
            ):
                score += 4.0
                matched_terms.add(term)

            # Attachment URLs
            if self._term_matches(
                term,
                url_text,
            ):
                score += 1.0
                matched_terms.add(term)

        # -----------------------------------------------------
        # No actual query match
        # -----------------------------------------------------

        if not matched_terms:
            return 0.0, []

        # -----------------------------------------------------
        # Exact / all-term title bonus
        # -----------------------------------------------------

        if query_terms:
            title_words = set(
                title.split()
            )

            if query_terms.issubset(
                title_words
            ):
                score += 15.0

        # -----------------------------------------------------
        # Supported attachment bonus
        #
        # ONLY applies after actual relevance exists.
        # -----------------------------------------------------

        supported_count = 0
        drive_count = 0

        for attachment in material.get(
            "materials",
            [],
        ):
            if (
                attachment.get("type")
                != "drive_file"
            ):
                continue

            drive_count += 1

            file_id = str(
                attachment.get(
                    "file_id",
                    "",
                )
            ).strip()

            if not file_id:
                continue

            try:
                info = (
                    self.classroom
                    .get_supported_file_info(
                        file_id
                    )
                )

                if info.get(
                    "supported"
                ):
                    supported_count += 1

            except ClassroomToolError:
                continue

        if drive_count > 0:
            score += 0.5

        if supported_count > 0:
            score += 1.0

        return (
            score,
            sorted(matched_terms),
        )

    # =========================================================
    # RESULT BUILDING
    # =========================================================

    def _build_result(
        self,
        *,
        material: dict[str, Any],
        score: float,
        matched_terms: list[str],
    ) -> dict[str, Any]:
        """
        Create clean discovery result for agents/services.
        """
        attachments: list[dict[str, Any]] = []

        for attachment in material.get(
            "materials",
            [],
        ):
            normalized_attachment = {
                "type": attachment.get(
                    "type",
                    "",
                ),
                "title": attachment.get(
                    "title",
                    "",
                ),
            }

            if attachment.get(
                "file_id"
            ):
                normalized_attachment[
                    "file_id"
                ] = attachment.get(
                    "file_id"
                )

            if attachment.get(
                "url"
            ):
                normalized_attachment[
                    "url"
                ] = attachment.get(
                    "url"
                )

            if (
                attachment.get("type")
                == "drive_file"
                and attachment.get("file_id")
            ):
                try:
                    support = (
                        self.classroom
                        .get_supported_file_info(
                            attachment[
                                "file_id"
                            ]
                        )
                    )

                    normalized_attachment[
                        "supported"
                    ] = support.get(
                        "supported",
                        False,
                    )

                    normalized_attachment[
                        "mode"
                    ] = support.get(
                        "mode",
                        "unsupported",
                    )

                    normalized_attachment[
                        "mime_type"
                    ] = support.get(
                        "mime_type",
                        "",
                    )

                    normalized_attachment[
                        "extension"
                    ] = support.get(
                        "extension",
                        "",
                    )

                except ClassroomToolError:
                    normalized_attachment[
                        "supported"
                    ] = False

                    normalized_attachment[
                        "mode"
                    ] = "inspection_failed"

            attachments.append(
                normalized_attachment
            )

        return {
            "course_id": material.get(
                "course_id",
                "",
            ),
            "material_id": material.get(
                "material_id",
                "",
            ),
            "title": material.get(
                "title",
                "",
            ),
            "description": material.get(
                "description",
                "",
            ),
            "state": material.get(
                "state",
                "",
            ),
            "alternate_link": material.get(
                "alternate_link",
                "",
            ),
            "relevance_score": round(
                score,
                4,
            ),
            "matched_terms": matched_terms,
            "attachments": attachments,
        }

    # =========================================================
    # TEXT PROCESSING
    # =========================================================

    @staticmethod
    def _normalize_text(
        value: Any,
    ) -> str:
        """
        Normalize text for matching.
        """
        text = str(
            value or ""
        ).lower()

        text = re.sub(
            r"[^a-z0-9]+",
            " ",
            text,
        )

        return " ".join(
            text.split()
        )

    @classmethod
    def _extract_terms(
        cls,
        query: str,
    ) -> set[str]:
        """
        Extract meaningful query terms.
        """
        normalized = cls._normalize_text(
            query
        )

        stopwords = {
            "the",
            "a",
            "an",
            "of",
            "for",
            "to",
            "in",
            "on",
            "and",
            "or",
            "with",
            "from",
            "make",
            "create",
            "give",
            "generate",
            "question",
            "questions",
            "test",
            "paper",
            "please",
            "using",
            "about",
            "explain",
        }

        return {
            term
            for term in normalized.split()
            if len(term) >= 2
            and term not in stopwords
        }

    @staticmethod
    def _term_matches(
        term: str,
        text: str,
    ) -> bool:
        """
        Check whether a term exists as a complete token.
        """
        if not term or not text:
            return False

        return term in text.split()

    # =========================================================
    # PRIORITY
    # =========================================================

    @staticmethod
    def _result_priority(
        result: dict[str, Any],
    ) -> int:
        """
        Tie-breaker.

        Prefer results containing more supported
        attachments, but ONLY among already-relevant
        results.
        """
        supported_count = 0

        for attachment in result.get(
            "attachments",
            [],
        ):
            if attachment.get(
                "supported"
            ) is True:
                supported_count += 1

        return supported_count

    # =========================================================
    # VALIDATION
    # =========================================================

    @staticmethod
    def _validate(
        *,
        course_id: str,
        query: str,
        top_k: int,
    ) -> None:
        if not course_id:
            raise ClassroomDiscoveryError(
                "course_id is required."
            )

        if not query:
            raise ClassroomDiscoveryError(
                "query is required."
            )

        if top_k <= 0:
            raise ClassroomDiscoveryError(
                "top_k must be greater than 0."
            )


def get_classroom_discovery_service() -> (
    ClassroomMaterialDiscoveryService
):
    """Return a default discovery service."""
    return ClassroomMaterialDiscoveryService()