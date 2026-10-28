from __future__ import annotations

import logging
from pathlib import Path
from time import perf_counter
from typing import Any

from backend.rag.loader import load_file
from backend.rag.vectorstore import index_documents
from backend.tools.classroom import ClassroomTool, ClassroomToolError


class ClassroomIngestionError(Exception):
    """Raised when Google Classroom material ingestion fails."""


logger = logging.getLogger(__name__)


class ClassroomIngestionService:
    """
    Google Classroom -> common RAG ingestion service.

    Supported:
    - PDF
    - PPTX
    - TXT
    - MD

    This service:
    - finds Classroom material
    - selects a Drive attachment
    - downloads it
    - loads it using the common loader
    - enriches metadata
    - indexes into ChromaDB
    """

    SUPPORTED_EXTENSIONS = {
        ".pdf",
        ".pptx",
        ".txt",
        ".md",
    }

    def __init__(
        self,
        classroom_tool: ClassroomTool | None = None,
        download_directory: str | Path | None = None,
    ) -> None:
        self.classroom = (
            classroom_tool
            or ClassroomTool()
        )

        project_root = Path(
            __file__
        ).resolve().parents[2]

        self.download_directory = Path(
            download_directory
            or project_root
            / "data"
            / "classroom_cache"
        )

        self.download_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    # =========================================================
    # PUBLIC API
    # =========================================================

    def ingest_material(
        self,
        *,
        course_id: str,
        material_id: str,
        teacher_id: str,
        school_id: str,
        conversation_id: str = "",
        drive_file_id: str | None = None,
        attachment_title: str | None = None,
    ) -> dict[str, Any]:
        """
        Find and ingest one specific Classroom material.

        Attachment selection priority:
        1. exact drive_file_id
        2. exact attachment_title
        3. first supported attachment
        """

        course_id = course_id.strip()
        material_id = material_id.strip()
        teacher_id = teacher_id.strip()
        school_id = school_id.strip()
        conversation_id = conversation_id.strip()

        requested_drive_file_id = (
            drive_file_id.strip()
            if drive_file_id
            else None
        )

        requested_attachment_title = (
            attachment_title.strip()
            if attachment_title
            else None
        )

        self._validate_required(
            course_id=course_id,
            material_id=material_id,
            teacher_id=teacher_id,
            school_id=school_id,
        )

        ingestion_started_at = perf_counter()

        # -----------------------------------------------------
        # 1. COURSE
        # -----------------------------------------------------

        stage_started_at = perf_counter()
        course = self._find_course(
            course_id=course_id
        )
        logger.info(
            "Classroom ingestion stage=course_lookup seconds=%.2f",
            perf_counter() - stage_started_at,
        )

        course_name = str(
            course.get(
                "name",
                "",
            )
        )

        # -----------------------------------------------------
        # 2. MATERIAL
        # -----------------------------------------------------

        stage_started_at = perf_counter()
        material = self._find_material(
            course_id=course_id,
            material_id=material_id,
        )
        logger.info(
            "Classroom ingestion stage=material_lookup seconds=%.2f",
            perf_counter() - stage_started_at,
        )

        # -----------------------------------------------------
        # 3. ATTACHMENT
        # -----------------------------------------------------

        attachment = self._find_supported_attachment(
            material,
            drive_file_id=requested_drive_file_id,
            attachment_title=requested_attachment_title,
        )

        if attachment is None:
            raise ClassroomIngestionError(
                "No supported Drive attachment was found "
                f"in Classroom material "
                f"'{material.get('title', '')}'. "
                "Supported types: PDF, PPTX, TXT, MD."
            )

        drive_file_id_value = str(
            attachment.get(
                "file_id",
                "",
            )
        ).strip()

        if not drive_file_id_value:
            raise ClassroomIngestionError(
                "Selected attachment does not contain "
                "a Drive file ID."
            )

        # -----------------------------------------------------
        # 4. DRIVE METADATA
        # -----------------------------------------------------

        stage_started_at = perf_counter()
        try:
            drive_info = (
                self.classroom.get_drive_file(
                    drive_file_id_value
                )
            )
        except ClassroomToolError as exc:
            raise ClassroomIngestionError(
                f"Could not read Drive metadata: {exc}"
            ) from exc
        logger.info(
            "Classroom ingestion stage=drive_metadata seconds=%.2f",
            perf_counter() - stage_started_at,
        )

        drive_name = str(
            drive_info.get(
                "name",
                attachment.get(
                    "title",
                    "",
                ),
            )
        ).strip()

        mime_type = str(
            drive_info.get(
                "mimeType",
                "",
            )
        ).strip()

        # -----------------------------------------------------
        # 5. DOWNLOAD
        # -----------------------------------------------------

        stage_started_at = perf_counter()
        try:
            download_result = (
                self.classroom.download_drive_file(
                    drive_file_id_value,
                    self.download_directory,
                )
            )
        except ClassroomToolError as exc:
            raise ClassroomIngestionError(
                f"Could not download Classroom file: {exc}"
            ) from exc
        logger.info(
            "Classroom ingestion stage=drive_download seconds=%.2f",
            perf_counter() - stage_started_at,
        )

        if not download_result.get(
            "success"
        ):
            raise ClassroomIngestionError(
                "Drive file could not be downloaded.\n"
                f"file_id={drive_file_id_value}\n"
                f"reason={download_result.get('reason')}"
            )

        local_file_path = Path(
            download_result["file_path"]
        )

        if not local_file_path.exists():
            raise ClassroomIngestionError(
                f"Downloaded file does not exist: "
                f"{local_file_path}"
            )

        extension = (
            local_file_path.suffix.lower()
        )

        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ClassroomIngestionError(
                f"Downloaded file type "
                f"'{extension}' is not supported."
            )

        # -----------------------------------------------------
        # 6. LOAD
        # -----------------------------------------------------

        stage_started_at = perf_counter()
        try:
            documents = load_file(
                str(local_file_path)
            )
        except Exception as exc:
            raise ClassroomIngestionError(
                f"Could not load downloaded Classroom "
                f"file '{local_file_path.name}': {exc}"
            ) from exc
        logger.info(
            "Classroom ingestion stage=file_load seconds=%.2f documents=%d",
            perf_counter() - stage_started_at,
            len(documents),
        )

        if not documents:
            raise ClassroomIngestionError(
                f"No readable content found in "
                f"'{local_file_path.name}'."
            )

        # -----------------------------------------------------
        # 7. METADATA
        # -----------------------------------------------------

        enriched_documents: list[
            dict[str, Any]
        ] = []

        for document in documents:
            text = str(
                document.get(
                    "text",
                    "",
                )
            ).strip()

            if not text:
                continue

            original_metadata = dict(
                document.get(
                    "metadata",
                    {},
                )
            )

            enriched_metadata = {
                **original_metadata,

                "source_type": "google_classroom",

                "teacher_id": teacher_id,
                "school_id": school_id,
                "conversation_id": conversation_id,

                "course_id": course_id,
                "course_name": course_name,

                "material_id": material_id,
                "material_title": material.get(
                    "title",
                    "",
                ),

                "drive_file_id": (
                    drive_file_id_value
                ),
                "drive_file_name": drive_name,
                "drive_mime_type": mime_type,

                "local_file_path": str(
                    local_file_path
                ),

                "file_name": original_metadata.get(
                    "file_name",
                    local_file_path.name,
                ),
            }

            enriched_documents.append(
                {
                    "text": text,
                    "metadata": enriched_metadata,
                }
            )

        if not enriched_documents:
            raise ClassroomIngestionError(
                "No valid documents remained after "
                "metadata processing."
            )

        # -----------------------------------------------------
        # 8. DETERMINISTIC SOURCE ID
        # -----------------------------------------------------

        source_id = (
            f"classroom"
            f"_teacher_{teacher_id}"
            f"_school_{school_id}"
            f"_course_{course_id}"
            f"_material_{material_id}"
            f"_drive_{drive_file_id_value}"
        )

        # -----------------------------------------------------
        # 9. INDEX
        # -----------------------------------------------------

        stage_started_at = perf_counter()
        try:
            chunk_count = index_documents(
                enriched_documents,
                source_id=source_id,
                chunk_size=800,
                chunk_overlap=100,
            )
        except Exception as exc:
            raise ClassroomIngestionError(
                f"Could not index Classroom material "
                f"into ChromaDB: {exc}"
            ) from exc
        logger.info(
            "Classroom ingestion stage=vector_index seconds=%.2f chunks=%d",
            perf_counter() - stage_started_at,
            chunk_count,
        )
        logger.info(
            "Classroom ingestion complete: seconds=%.2f",
            perf_counter() - ingestion_started_at,
        )

        return {
            "success": True,

            "source_type": "google_classroom",

            "teacher_id": teacher_id,
            "school_id": school_id,
            "conversation_id": conversation_id,

            "course_id": course_id,
            "course_name": course_name,

            "material_id": material_id,
            "material_title": material.get(
                "title",
                "",
            ),

            "drive_file_id": (
                drive_file_id_value
            ),
            "drive_file_name": drive_name,
            "drive_mime_type": mime_type,

            "attachment_title": attachment.get(
                "title",
                "",
            ),

            "file_name": local_file_path.name,
            "file_path": str(local_file_path),
            "file_type": extension.lstrip("."),

            "document_count": len(
                enriched_documents
            ),
            "chunk_count": chunk_count,

            "source_id": source_id,
        }

    # =========================================================
    # COURSE
    # =========================================================

    def _find_course(
        self,
        *,
        course_id: str,
    ) -> dict[str, Any]:

        try:
            courses = (
                self.classroom.list_courses()
            )
        except ClassroomToolError as exc:
            raise ClassroomIngestionError(
                f"Could not list Classroom courses: {exc}"
            ) from exc

        for course in courses:
            if (
                str(
                    course.get(
                        "id",
                        "",
                    )
                ).strip()
                == course_id
            ):
                return course

        raise ClassroomIngestionError(
            f"Classroom course "
            f"'{course_id}' was not found."
        )

    # =========================================================
    # MATERIAL
    # =========================================================

    def _find_material(
        self,
        *,
        course_id: str,
        material_id: str,
    ) -> dict[str, Any]:

        try:
            materials = (
                self.classroom
                .list_course_materials(
                    course_id
                )
            )
        except ClassroomToolError as exc:
            raise ClassroomIngestionError(
                f"Could not list Classroom materials: {exc}"
            ) from exc

        for material in materials:
            current_id = str(
                material.get(
                    "material_id",
                    "",
                )
            ).strip()

            if current_id == material_id:
                return material

        raise ClassroomIngestionError(
            f"Classroom material "
            f"'{material_id}' was not found "
            f"in course '{course_id}'."
        )

    # =========================================================
    # ATTACHMENT
    # =========================================================

    def _find_supported_attachment(
        self,
        material: dict[str, Any],
        *,
        drive_file_id: str | None = None,
        attachment_title: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Find a supported Drive attachment.

        Priority:
        1. exact Drive ID
        2. exact title
        3. first supported attachment
        """

        requested_file_id = (
            drive_file_id.strip()
            if drive_file_id
            else ""
        )

        requested_title = (
            attachment_title.strip().lower()
            if attachment_title
            else ""
        )

        attachments = material.get(
            "materials",
            [],
        )

        # -----------------------------------------------------
        # Exact Drive ID
        # -----------------------------------------------------

        if requested_file_id:
            for attachment in attachments:

                if (
                    attachment.get(
                        "type"
                    )
                    != "drive_file"
                ):
                    continue

                current_id = str(
                    attachment.get(
                        "file_id",
                        "",
                    )
                ).strip()

                if (
                    current_id
                    != requested_file_id
                ):
                    continue

                return self._validate_attachment(
                    attachment
                )

        # -----------------------------------------------------
        # Exact attachment title
        # -----------------------------------------------------

        if requested_title:
            for attachment in attachments:

                if (
                    attachment.get(
                        "type"
                    )
                    != "drive_file"
                ):
                    continue

                title = str(
                    attachment.get(
                        "title",
                        "",
                    )
                ).strip().lower()

                if (
                    title
                    != requested_title
                ):
                    continue

                validated = (
                    self._validate_attachment(
                        attachment
                    )
                )

                if validated is not None:
                    return validated

        # -----------------------------------------------------
        # First supported attachment
        # -----------------------------------------------------

        for attachment in attachments:

            if (
                attachment.get(
                    "type"
                )
                != "drive_file"
            ):
                continue

            validated = (
                self._validate_attachment(
                    attachment
                )
            )

            if validated is not None:
                return validated

        return None

    def _validate_attachment(
        self,
        attachment: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Return attachment when its file type is supported."""

        file_id = str(
            attachment.get(
                "file_id",
                "",
            )
        ).strip()

        if not file_id:
            return None

        try:
            info = (
                self.classroom
                .get_supported_file_info(
                    file_id
                )
            )
        except ClassroomToolError:
            return None

        if not info.get(
            "supported"
        ):
            return None

        extension = str(
            info.get(
                "extension",
                "",
            )
        ).lower()

        if (
            extension
            not in self.SUPPORTED_EXTENSIONS
        ):
            return None

        return attachment

    # =========================================================
    # VALIDATION
    # =========================================================

    @staticmethod
    def _validate_required(
        *,
        course_id: str,
        material_id: str,
        teacher_id: str,
        school_id: str,
    ) -> None:

        values = {
            "course_id": course_id,
            "material_id": material_id,
            "teacher_id": teacher_id,
            "school_id": school_id,
        }

        for name, value in values.items():
            if not value:
                raise ClassroomIngestionError(
                    f"{name} is required."
                )


def get_classroom_ingestion_service() -> (
    ClassroomIngestionService
):
    """Return default Classroom ingestion service."""
    return ClassroomIngestionService()