from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload


class ClassroomToolError(Exception):
    """Raised when Google Classroom integration fails."""


class ClassroomTool:
    """
    Read-only Google Classroom + Google Drive integration.
    """

    SCOPES = [
        "https://www.googleapis.com/auth/classroom.courseworkmaterials.readonly",
        "https://www.googleapis.com/auth/classroom.courses.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]

    DEFAULT_CREDENTIALS_FILE = "credentials.json"
    DEFAULT_TOKEN_FILE = "token.json"

    SUPPORTED_DIRECT_DOWNLOAD_MIME_TYPES = {
        "application/pdf": ".pdf",
        "text/plain": ".txt",
        "text/markdown": ".md",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    }

    GOOGLE_WORKSPACE_EXPORT_TYPES = {
        "application/vnd.google-apps.document": (
            "text/plain",
            ".txt",
        ),
        "application/vnd.google-apps.spreadsheet": (
            "text/csv",
            ".csv",
        ),
        "application/vnd.google-apps.presentation": (
            "application/pdf",
            ".pdf",
        ),
    }

    def __init__(
        self,
        *,
        credentials_file: str | None = None,
        token_file: str | None = None,
    ) -> None:
        self.credentials_file = Path(
            credentials_file
            or os.getenv(
                "GOOGLE_CREDENTIALS_FILE",
                self.DEFAULT_CREDENTIALS_FILE,
            )
        )

        self.token_file = Path(
            token_file
            or os.getenv(
                "GOOGLE_CLASSROOM_TOKEN_FILE",
                self.DEFAULT_TOKEN_FILE,
            )
        )

        self._classroom_service = None
        self._drive_service = None

    # =========================================================
    # AUTH
    # =========================================================

    def _load_credentials(
        self,
    ) -> Credentials:
        credentials: Credentials | None = None

        if self.token_file.exists():
            try:
                credentials = (
                    Credentials
                    .from_authorized_user_file(
                        str(self.token_file),
                        self.SCOPES,
                    )
                )
            except Exception as exc:
                raise ClassroomToolError(
                    f"Could not read OAuth token file "
                    f"'{self.token_file}': {exc}"
                ) from exc

        if credentials and credentials.valid:
            return credentials

        if (
            credentials
            and credentials.expired
            and credentials.refresh_token
        ):
            try:
                credentials.refresh(
                    Request()
                )
            except Exception as exc:
                raise ClassroomToolError(
                    f"Could not refresh Google OAuth token: "
                    f"{exc}"
                ) from exc

            self._save_credentials(
                credentials
            )

            return credentials

        if not self.credentials_file.exists():
            raise ClassroomToolError(
                "Google OAuth credentials file not found.\n"
                f"Expected: {self.credentials_file}"
            )

        try:
            flow = (
                InstalledAppFlow
                .from_client_secrets_file(
                    str(self.credentials_file),
                    self.SCOPES,
                )
            )

            credentials = (
                flow.run_local_server(
                    port=0,
                    access_type="offline",
                    prompt="consent",
                )
            )

        except Exception as exc:
            raise ClassroomToolError(
                f"Google OAuth authentication failed: "
                f"{exc}"
            ) from exc

        self._save_credentials(
            credentials
        )

        return credentials

    def _save_credentials(
        self,
        credentials: Credentials,
    ) -> None:
        try:
            self.token_file.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            self.token_file.write_text(
                credentials.to_json(),
                encoding="utf-8",
            )

        except Exception as exc:
            raise ClassroomToolError(
                f"Could not save OAuth token: {exc}"
            ) from exc

    # =========================================================
    # SERVICES
    # =========================================================

    def _get_classroom_service(self):
        if self._classroom_service is not None:
            return self._classroom_service

        credentials = self._load_credentials()

        try:
            self._classroom_service = build(
                "classroom",
                "v1",
                credentials=credentials,
                cache_discovery=False,
            )
        except Exception as exc:
            raise ClassroomToolError(
                f"Could not initialize Google Classroom API: "
                f"{exc}"
            ) from exc

        return self._classroom_service

    def _get_drive_service(self):
        if self._drive_service is not None:
            return self._drive_service

        credentials = self._load_credentials()

        try:
            self._drive_service = build(
                "drive",
                "v3",
                credentials=credentials,
                cache_discovery=False,
            )
        except Exception as exc:
            raise ClassroomToolError(
                f"Could not initialize Google Drive API: "
                f"{exc}"
            ) from exc

        return self._drive_service

    # =========================================================
    # COURSES
    # =========================================================

    def list_courses(
        self,
        *,
        course_state: str = "ACTIVE",
        page_size: int = 100,
    ) -> list[dict[str, Any]]:

        if not course_state.strip():
            raise ClassroomToolError(
                "course_state cannot be empty."
            )

        if page_size <= 0:
            raise ClassroomToolError(
                "page_size must be greater than 0."
            )

        service = self._get_classroom_service()

        courses: list[
            dict[str, Any]
        ] = []

        page_token: str | None = None

        try:
            while True:
                response = (
                    service.courses()
                    .list(
                        courseStates=[
                            course_state
                        ],
                        pageSize=page_size,
                        pageToken=page_token,
                    )
                    .execute()
                )

                courses.extend(
                    response.get(
                        "courses",
                        [],
                    )
                )

                page_token = response.get(
                    "nextPageToken"
                )

                if not page_token:
                    break

        except HttpError as exc:
            raise ClassroomToolError(
                f"Google Classroom course listing failed: "
                f"{exc}"
            ) from exc

        return courses

    # =========================================================
    # COURSE MATERIALS
    # =========================================================

    def list_course_materials(
        self,
        course_id: str,
        *,
        page_size: int = 100,
    ) -> list[dict[str, Any]]:

        course_id = course_id.strip()

        if not course_id:
            raise ClassroomToolError(
                "course_id is required."
            )

        if page_size <= 0:
            raise ClassroomToolError(
                "page_size must be greater than 0."
            )

        service = self._get_classroom_service()

        materials: list[
            dict[str, Any]
        ] = []

        page_token: str | None = None

        try:
            while True:
                response = (
                    service.courses()
                    .courseWorkMaterials()
                    .list(
                        courseId=course_id,
                        pageSize=page_size,
                        pageToken=page_token,
                    )
                    .execute()
                )

                for item in response.get(
                    "courseWorkMaterial",
                    [],
                ):
                    materials.append(
                        self._normalize_course_material(
                            item,
                            course_id=course_id,
                        )
                    )

                page_token = response.get(
                    "nextPageToken"
                )

                if not page_token:
                    break

        except HttpError as exc:
            raise ClassroomToolError(
                f"Google Classroom material listing failed: "
                f"{exc}"
            ) from exc

        return materials

    def _normalize_course_material(
        self,
        item: dict[str, Any],
        *,
        course_id: str,
    ) -> dict[str, Any]:

        normalized = {
            "course_id": course_id,
            "material_id": item.get(
                "id"
            ),
            "title": item.get(
                "title",
                "",
            ),
            "description": item.get(
                "description",
                "",
            ),
            "state": item.get(
                "state",
                "",
            ),
            "alternate_link": item.get(
                "alternateLink",
                "",
            ),
            "creation_time": item.get(
                "creationTime",
                "",
            ),
            "update_time": item.get(
                "updateTime",
                "",
            ),
            "materials": [],
            "raw": item,
        }

        for material in item.get(
            "materials",
            [],
        ):
            normalized_material = (
                self._normalize_attachment(
                    material
                )
            )

            if normalized_material:
                normalized[
                    "materials"
                ].append(
                    normalized_material
                )

        return normalized

    def _normalize_attachment(
        self,
        material: dict[str, Any],
    ) -> dict[str, Any] | None:

        if "driveFile" in material:
            shared_drive_file = material.get(
                "driveFile",
                {},
            )

            drive_file = (
                shared_drive_file.get(
                    "driveFile",
                    {},
                )
            )

            return {
                "type": "drive_file",
                "file_id": drive_file.get(
                    "id"
                ),
                "title": drive_file.get(
                    "title",
                    "",
                ),
                "alternate_link": drive_file.get(
                    "alternateLink",
                    "",
                ),
                "share_mode": shared_drive_file.get(
                    "shareMode",
                    "",
                ),
                "raw": material,
            }

        if "link" in material:
            link = material.get(
                "link",
                {},
            )

            return {
                "type": "link",
                "title": link.get(
                    "title",
                    "",
                ),
                "url": link.get(
                    "url",
                    "",
                ),
                "raw": material,
            }

        if "youtubeVideo" in material:
            youtube = material.get(
                "youtubeVideo",
                {},
            )

            return {
                "type": "youtube",
                "title": youtube.get(
                    "title",
                    "",
                ),
                "url": youtube.get(
                    "alternateLink",
                    youtube.get(
                        "url",
                        "",
                    ),
                ),
                "video_id": youtube.get(
                    "id",
                    "",
                ),
                "raw": material,
            }

        if "form" in material:
            form = material.get(
                "form",
                {},
            )

            return {
                "type": "form",
                "title": form.get(
                    "title",
                    "",
                ),
                "url": form.get(
                    "formUrl",
                    form.get(
                        "responseUrl",
                        "",
                    ),
                ),
                "form_id": form.get(
                    "formId",
                    "",
                ),
                "raw": material,
            }

        return None

    # =========================================================
    # DRIVE METADATA
    # =========================================================

    def get_drive_file(
        self,
        file_id: str,
    ) -> dict[str, Any]:

        file_id = file_id.strip()

        if not file_id:
            raise ClassroomToolError(
                "file_id is required."
            )

        service = self._get_drive_service()

        try:
            return (
                service.files()
                .get(
                    fileId=file_id,
                    fields=(
                        "id,"
                        "name,"
                        "mimeType,"
                        "webViewLink,"
                        "modifiedTime,"
                        "size,"
                        "capabilities(canDownload)"
                    ),
                    supportsAllDrives=True,
                )
                .execute()
            )

        except HttpError as exc:
            raise ClassroomToolError(
                f"Could not read Drive file "
                f"'{file_id}': {exc}"
            ) from exc

    # =========================================================
    # FILE SUPPORT
    # =========================================================

    def get_supported_file_info(
        self,
        file_id: str,
    ) -> dict[str, Any]:

        metadata = self.get_drive_file(
            file_id
        )

        mime_type = str(
            metadata.get(
                "mimeType",
                "",
            )
        ).strip()

        if (
            mime_type
            in self.SUPPORTED_DIRECT_DOWNLOAD_MIME_TYPES
        ):
            return {
                "supported": True,
                "mode": "download",
                "mime_type": mime_type,
                "extension": (
                    self.SUPPORTED_DIRECT_DOWNLOAD_MIME_TYPES[
                        mime_type
                    ]
                ),
                "metadata": metadata,
            }

        if mime_type in (
            self.GOOGLE_WORKSPACE_EXPORT_TYPES
        ):
            export_mime_type, extension = (
                self.GOOGLE_WORKSPACE_EXPORT_TYPES[
                    mime_type
                ]
            )

            return {
                "supported": True,
                "mode": "export",
                "mime_type": mime_type,
                "export_mime_type": export_mime_type,
                "extension": extension,
                "metadata": metadata,
            }

        return {
            "supported": False,
            "mode": "unsupported",
            "mime_type": mime_type,
            "extension": "",
            "metadata": metadata,
        }

    # =========================================================
    # DOWNLOAD
    # =========================================================

    def download_drive_file(
        self,
        file_id: str,
        output_directory: str | Path,
        *,
        output_name: str | None = None,
    ) -> dict[str, Any]:

        file_id = file_id.strip()

        if not file_id:
            raise ClassroomToolError(
                "file_id is required."
            )

        output_directory = Path(
            output_directory
        )

        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        support = (
            self.get_supported_file_info(
                file_id
            )
        )

        if not support.get(
            "supported"
        ):
            return {
                "success": False,
                "file_id": file_id,
                "reason": "unsupported_file_type",
                "mime_type": support.get(
                    "mime_type",
                    "",
                ),
                "metadata": support.get(
                    "metadata",
                    {},
                ),
            }

        metadata = support.get(
            "metadata",
            {},
        )

        original_name = str(
            metadata.get(
                "name",
                "",
            )
        ).strip()

        if not original_name:
            original_name = (
                f"{file_id}"
                f"{support.get('extension', '')}"
            )

        if output_name:
            filename = Path(
                output_name
            ).name
        else:
            filename = original_name

            if not Path(filename).suffix:
                filename += support.get(
                    "extension",
                    "",
                )

        output_path = (
            output_directory / filename
        )

        if output_path.exists():
            output_path.unlink()

        service = self._get_drive_service()

        try:
            if support["mode"] == "export":
                request = (
                    service.files()
                    .export_media(
                        fileId=file_id,
                        mimeType=support[
                            "export_mime_type"
                        ],
                    )
                )
            else:
                request = (
                    service.files()
                    .get_media(
                        fileId=file_id
                    )
                )

            buffer = io.BytesIO()

            downloader = (
                MediaIoBaseDownload(
                    buffer,
                    request,
                )
            )

            done = False

            while not done:
                status, done = (
                    downloader.next_chunk()
                )

                if status is not None:
                    print(
                        f"Downloading "
                        f"{original_name}: "
                        f"{int(status.progress() * 100)}%"
                    )

            file_bytes = buffer.getvalue()

            if not file_bytes:
                raise ClassroomToolError(
                    f"Google Drive returned an empty file "
                    f"for '{original_name}'."
                )

            # -------------------------------------------------
            # PDF VALIDATION
            # -------------------------------------------------

            if (
                support["mime_type"]
                == "application/pdf"
            ):
                if not file_bytes.startswith(
                    b"%PDF-"
                ):
                    raise ClassroomToolError(
                        "Downloaded content is not a valid PDF."
                    )

            # -------------------------------------------------
            # PPTX VALIDATION
            # -------------------------------------------------

            if (
                support["mime_type"]
                == (
                    "application/"
                    "vnd.openxmlformats-officedocument."
                    "presentationml.presentation"
                )
            ):
                # DOCX/PPTX/XLSX files are ZIP-based Office
                # packages and normally start with PK.
                if not file_bytes.startswith(
                    b"PK"
                ):
                    raise ClassroomToolError(
                        "Downloaded content is not a valid PPTX."
                    )

            output_path.write_bytes(
                file_bytes
            )

        except HttpError as exc:
            raise ClassroomToolError(
                f"Could not download Drive file "
                f"'{file_id}': {exc}"
            ) from exc

        except ClassroomToolError:
            raise

        except Exception as exc:
            raise ClassroomToolError(
                f"Could not save Drive file "
                f"'{file_id}': {exc}"
            ) from exc

        return {
            "success": True,
            "file_id": file_id,
            "file_path": str(
                output_path
            ),
            "file_name": output_path.name,
            "mime_type": support.get(
                "mime_type",
                "",
            ),
            "mode": support.get(
                "mode",
                "",
            ),
            "size_bytes": len(
                file_bytes
            ),
            "metadata": metadata,
        }

    # =========================================================
    # SEARCH
    # =========================================================

    def search_course_materials(
        self,
        course_id: str,
        query: str,
    ) -> list[dict[str, Any]]:

        course_id = course_id.strip()
        query = query.strip().lower()

        if not course_id:
            raise ClassroomToolError(
                "course_id is required."
            )

        if not query:
            raise ClassroomToolError(
                "query is required."
            )

        materials = (
            self.list_course_materials(
                course_id
            )
        )

        query_terms = {
            term
            for term in query.split()
            if len(term) >= 2
        }

        scored: list[
            tuple[int, dict[str, Any]]
        ] = []

        for material in materials:
            searchable_text = " ".join(
                [
                    str(
                        material.get(
                            "title",
                            "",
                        )
                    ),
                    str(
                        material.get(
                            "description",
                            "",
                        )
                    ),
                ]
            ).lower()

            score = sum(
                1
                for term in query_terms
                if term in searchable_text
            )

            for attachment in material.get(
                "materials",
                [],
            ):
                attachment_text = " ".join(
                    [
                        str(
                            attachment.get(
                                "title",
                                "",
                            )
                        ),
                        str(
                            attachment.get(
                                "url",
                                "",
                            )
                        ),
                    ]
                ).lower()

                score += sum(
                    1
                    for term in query_terms
                    if term in attachment_text
                )

            if score > 0:
                scored.append(
                    (
                        score,
                        material,
                    )
                )

        scored.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        results = []

        for score, material in scored:
            result = dict(
                material
            )

            result[
                "relevance_score"
            ] = score

            results.append(
                result
            )

        return results


def get_classroom_tool() -> ClassroomTool:
    """Return default ClassroomTool."""
    return ClassroomTool()


def list_courses() -> list[dict[str, Any]]:
    """Convenience wrapper."""
    return get_classroom_tool().list_courses()


def list_course_materials(
    course_id: str,
) -> list[dict[str, Any]]:
    """Convenience wrapper."""
    return get_classroom_tool().list_course_materials(
        course_id
    )