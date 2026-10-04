from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.rag.loader import load_file
from backend.rag.vectorstore import index_documents


class FileIngestionError(Exception):
    """Raised when teacher file ingestion fails."""


class TeacherFileIngestionService:
    """
    Ingest teacher-provided files into the common RAG pipeline.

    Supported:
    - PDF
    - PPTX
    - TXT
    - MD
    """

    SUPPORTED_EXTENSIONS = {
        ".pdf",
        ".pptx",
        ".txt",
        ".md",
    }

    def ingest(
        self,
        file_path: str | Path,
        *,
        teacher_id: str,
        school_id: str,
        conversation_id: str = "",
    ) -> dict[str, Any]:

        path = Path(file_path)

        teacher_id = teacher_id.strip()
        school_id = school_id.strip()
        conversation_id = conversation_id.strip()

        if not teacher_id:
            raise FileIngestionError(
                "teacher_id is required."
            )

        if not school_id:
            raise FileIngestionError(
                "school_id is required."
            )

        if not path.exists():
            raise FileIngestionError(
                f"File not found: {path}"
            )

        if not path.is_file():
            raise FileIngestionError(
                f"Path is not a file: {path}"
            )

        extension = path.suffix.lower()

        if extension not in self.SUPPORTED_EXTENSIONS:
            raise FileIngestionError(
                f"Unsupported file type '{extension}'. "
                "Supported: "
                ".pdf, .pptx, .txt, .md"
            )

        try:
            documents = load_file(
                str(path)
            )
        except Exception as exc:
            raise FileIngestionError(
                f"Could not load '{path.name}': {exc}"
            ) from exc

        if not documents:
            raise FileIngestionError(
                f"No readable content found in "
                f"'{path.name}'."
            )

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
                "source_type": "teacher_file",
                "teacher_id": teacher_id,
                "school_id": school_id,
                "conversation_id": conversation_id,
                "file_name": original_metadata.get(
                    "file_name",
                    path.name,
                ),
            }

            enriched_documents.append(
                {
                    "text": text,
                    "metadata": enriched_metadata,
                }
            )

        if not enriched_documents:
            raise FileIngestionError(
                "No valid documents remained after "
                "metadata processing."
            )

        source_id = (
            f"teacher_{teacher_id}"
            f"_school_{school_id}"
            f"_conversation_{conversation_id}"
            f"_{path.name}"
        )

        try:
            chunk_count = index_documents(
                enriched_documents,
                source_id=source_id,
                chunk_size=800,
                chunk_overlap=100,
            )
        except Exception as exc:
            raise FileIngestionError(
                f"Could not index '{path.name}': {exc}"
            ) from exc

        return {
            "success": True,
            "file_name": path.name,
            "file_path": str(path),
            "file_type": extension.lstrip("."),
            "teacher_id": teacher_id,
            "school_id": school_id,
            "conversation_id": conversation_id,
            "source_type": "teacher_file",
            "document_count": len(
                enriched_documents
            ),
            "chunk_count": chunk_count,
            "source_id": source_id,
        }