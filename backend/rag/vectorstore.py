from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer


# =============================================================
# PROJECT PATHS / CONFIG
# =============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

VECTORSTORE_PATH = (
    PROJECT_ROOT
    / "data"
    / "chroma"
)

COLLECTION_NAME = "tco_documents"

EMBEDDING_MODEL_NAME = (
    "sentence-transformers/all-MiniLM-L6-v2"
)

DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 100


# =============================================================
# CHROMA
# =============================================================

client = chromadb.PersistentClient(
    path=str(VECTORSTORE_PATH)
)

collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={
        "hnsw:space": "cosine",
    },
)


# =============================================================
# EMBEDDINGS
# =============================================================

embedding_model = SentenceTransformer(
    EMBEDDING_MODEL_NAME
)


# =============================================================
# ERRORS
# =============================================================

class VectorStoreError(Exception):
    """Raised when vector-store operations fail."""


# =============================================================
# TEXT NORMALIZATION
# =============================================================

def _normalize_text(
    text: str,
) -> str:
    """
    Normalize whitespace while preserving the actual content.
    """
    return re.sub(
        r"\s+",
        " ",
        str(text or ""),
    ).strip()


# =============================================================
# SAFE ID HELPERS
# =============================================================

def _sanitize_id_part(
    value: Any,
) -> str:
    """
    Convert a value into a Chroma-safe deterministic ID fragment.
    """
    text = str(
        value or ""
    ).strip().lower()

    text = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        text,
    )

    text = text.strip(
        "_"
    )

    return text or "unknown"


def _build_chunk_id(
    *,
    source_id: str,
    metadata: dict[str, Any],
    document_index: int,
    chunk_in_document: int,
    text: str,
) -> str:
    """
    Build a deterministic, collision-resistant chunk ID.

    Identity hierarchy:

        source_id
        + document locator
        + chunk index
        + content hash

    Document locator preference:
        page
        slide
        document_index

    Why content hash is included:
    - prevents accidental collisions
    - keeps IDs deterministic
    - gives extra protection if metadata is incomplete

    The page/slide/document index is essential because multiple
    documents can each have chunk 0.
    """
    source_part = _sanitize_id_part(
        source_id
    )

    file_name_part = _sanitize_id_part(
        metadata.get(
            "file_name",
            "document",
        )
    )

    # ---------------------------------------------------------
    # Prefer page
    # ---------------------------------------------------------

    if metadata.get(
        "page"
    ) is not None:
        locator_name = "page"
        locator_value = metadata.get(
            "page"
        )

    # ---------------------------------------------------------
    # Then slide
    # ---------------------------------------------------------

    elif metadata.get(
        "slide"
    ) is not None:
        locator_name = "slide"
        locator_value = metadata.get(
            "slide"
        )

    # ---------------------------------------------------------
    # Fallback to document index
    # ---------------------------------------------------------

    else:
        locator_name = "document"
        locator_value = (
            document_index + 1
        )

    content_hash = hashlib.sha256(
        text.encode(
            "utf-8",
            errors="ignore",
        )
    ).hexdigest()[:12]

    return (
        f"{source_part}"
        f"_{file_name_part}"
        f"_{locator_name}_{_sanitize_id_part(locator_value)}"
        f"_chunk_{chunk_in_document}"
        f"_{content_hash}"
    )


# =============================================================
# CHUNKING
# =============================================================

def create_chunks(
    text: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """
    Split text into overlapping chunks.

    Parameters:
        chunk_size:
            Maximum approximate character size of a chunk.

        chunk_overlap:
            Number of characters shared with the previous chunk.
    """
    if chunk_size <= 0:
        raise VectorStoreError(
            "chunk_size must be greater than 0."
        )

    if chunk_overlap < 0:
        raise VectorStoreError(
            "chunk_overlap cannot be negative."
        )

    if chunk_overlap >= chunk_size:
        raise VectorStoreError(
            "chunk_overlap must be smaller than chunk_size."
        )

    text = str(
        text or ""
    ).strip()

    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []

    start = 0
    text_length = len(text)

    while start < text_length:

        end = min(
            start + chunk_size,
            text_length,
        )

        chunk = text[
            start:end
        ].strip()

        if chunk:
            chunks.append(
                chunk
            )

        if end >= text_length:
            break

        next_start = (
            end - chunk_overlap
        )

        if next_start <= start:
            raise VectorStoreError(
                "Chunking failed to advance. "
                "Check chunk_size and chunk_overlap."
            )

        start = next_start

    return chunks


# =============================================================
# EMBEDDINGS
# =============================================================

def _embed_texts(
    texts: list[str],
) -> list[list[float]]:
    """
    Create normalized embeddings.
    """
    if not texts:
        return []

    try:
        embeddings = embedding_model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

    except Exception as exc:
        raise VectorStoreError(
            f"Could not create embeddings: {exc}"
        ) from exc

    return embeddings.tolist()


# =============================================================
# DOCUMENT PREPARATION
# =============================================================

def _prepare_chunks(
    documents: list[dict[str, Any]],
    *,
    source_id: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[dict[str, Any]]:
    """
    Convert loaded documents into uniquely identifiable chunks.

    IMPORTANT:
    Chunking happens independently for every document.

    For a PDF:
        page 1 -> chunk 0
        page 2 -> chunk 0

    For a PPTX:
        slide 1 -> chunk 0
        slide 2 -> chunk 0

    These are different chunks and MUST have different IDs.
    """
    prepared_chunks: list[
        dict[str, Any]
    ] = []

    for document_index, document in enumerate(
        documents
    ):
        text = _normalize_text(
            document.get(
                "text",
                "",
            )
        )

        if not text:
            continue

        original_metadata = dict(
            document.get(
                "metadata",
                {},
            )
        )

        chunks = create_chunks(
            text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        for chunk_in_document, chunk_text in enumerate(
            chunks
        ):
            metadata = {
                **original_metadata,

                # Store the source ID in metadata so future
                # operations can identify this exact ingestion.
                "source_id": source_id,

                # Local chunk position.
                "chunk_in_document": (
                    chunk_in_document
                ),

                # Global document position.
                "document_index": (
                    document_index
                ),
            }

            chunk_id = _build_chunk_id(
                source_id=source_id,
                metadata=metadata,
                document_index=document_index,
                chunk_in_document=chunk_in_document,
                text=chunk_text,
            )

            prepared_chunks.append(
                {
                    "id": chunk_id,
                    "text": chunk_text,
                    "metadata": metadata,
                }
            )

    return prepared_chunks


# =============================================================
# INDEX DOCUMENTS
# =============================================================

def index_documents(
    documents: list[dict[str, Any]],
    *,
    source_id: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> int:
    """
    Index documents into ChromaDB.

    Returns:
        Number of chunks indexed.

    The operation is deterministic:
    ingesting the same source repeatedly produces the same
    chunk IDs.
    """
    if not isinstance(
        documents,
        list,
    ):
        raise VectorStoreError(
            "documents must be a list."
        )

    source_id = str(
        source_id or ""
    ).strip()

    if not source_id:
        raise VectorStoreError(
            "source_id is required."
        )

    prepared_chunks = _prepare_chunks(
        documents,
        source_id=source_id,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    if not prepared_chunks:
        return 0

    ids = [
        chunk["id"]
        for chunk in prepared_chunks
    ]

    texts = [
        chunk["text"]
        for chunk in prepared_chunks
    ]

    metadatas = [
        chunk["metadata"]
        for chunk in prepared_chunks
    ]

    # ---------------------------------------------------------
    # Safety check:
    # IDs must be unique INSIDE this request.
    # ---------------------------------------------------------

    if len(ids) != len(
        set(ids)
    ):
        duplicates = sorted(
            {
                item
                for item in ids
                if ids.count(item) > 1
            }
        )

        raise VectorStoreError(
            "Duplicate chunk IDs generated before Chroma upsert:\n"
            + "\n".join(
                duplicates
            )
        )

    embeddings = _embed_texts(
        texts
    )

    try:
        collection.upsert(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings,
        )
    except Exception as exc:
        raise VectorStoreError(
            f"Could not index chunks into ChromaDB: {exc}"
        ) from exc

    return len(
        prepared_chunks
    )


# =============================================================
# INDEX FILE
# =============================================================

def index_file(
    file_path: str,
    *,
    loader,
    source_id: str | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> int:
    """
    Generic file indexing helper.

    `loader` must expose:
        load_file(file_path) -> list[dict]
    """
    path = Path(
        file_path
    )

    if not path.exists():
        raise VectorStoreError(
            f"File not found: {path}"
        )

    if source_id is None:
        source_id = str(
            path
        )

    try:
        documents = loader.load_file(
            str(path)
        )
    except Exception as exc:
        raise VectorStoreError(
            f"Could not load file '{path.name}': {exc}"
        ) from exc

    return index_documents(
        documents,
        source_id=source_id,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


# =============================================================
# PDF COMPATIBILITY
# =============================================================

def index_pdf(
    file_path: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> int:
    """
    Backward-compatible PDF indexing function.
    """
    from backend.rag.loader import load_pdf

    path = Path(
        file_path
    )

    if not path.exists():
        raise VectorStoreError(
            f"PDF file not found: {path}"
        )

    documents = load_pdf(
        str(path)
    )

    return index_documents(
        documents,
        source_id=str(path),
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


# =============================================================
# COUNTS
# =============================================================

def get_collection_count() -> int:
    """Return total number of Chroma chunks."""
    try:
        return collection.count()
    except Exception as exc:
        raise VectorStoreError(
            f"Could not read Chroma collection count: {exc}"
        ) from exc


# =============================================================
# SOURCE RETRIEVAL
# =============================================================

def get_source_chunks(
    source: str,
) -> list[dict[str, Any]]:
    """
    Retrieve chunks belonging to an exact source path/value.

    Existing projects historically used the `source` metadata
    field as the source identifier, so this helper preserves
    that behavior.
    """
    source = str(
        source or ""
    ).strip()

    if not source:
        raise VectorStoreError(
            "source is required."
        )

    try:
        result = collection.get(
            include=[
                "documents",
                "metadatas",
            ]
        )
    except Exception as exc:
        raise VectorStoreError(
            f"Could not read Chroma collection: {exc}"
        ) from exc

    ids = result.get(
        "ids",
        [],
    )

    documents = result.get(
        "documents",
        [],
    )

    metadatas = result.get(
        "metadatas",
        [],
    )

    chunks: list[
        dict[str, Any]
    ] = []

    for index, document_id in enumerate(
        ids
    ):
        metadata = (
            metadatas[index]
            if index < len(metadatas)
            else {}
        )

        document = (
            documents[index]
            if index < len(documents)
            else ""
        )

        metadata = metadata or {}

        if (
            str(
                metadata.get(
                    "source",
                    "",
                )
            )
            == source
        ):
            chunks.append(
                {
                    "id": document_id,
                    "text": document,
                    "metadata": metadata,
                }
            )

    return chunks


# =============================================================
# SOURCE ID RETRIEVAL
# =============================================================

def get_source_id_chunks(
    source_id: str,
) -> list[dict[str, Any]]:
    """
    Retrieve chunks belonging to a deterministic source_id.
    """
    source_id = str(
        source_id or ""
    ).strip()

    if not source_id:
        raise VectorStoreError(
            "source_id is required."
        )

    try:
        result = collection.get(
            include=[
                "documents",
                "metadatas",
            ]
        )
    except Exception as exc:
        raise VectorStoreError(
            f"Could not read Chroma collection: {exc}"
        ) from exc

    ids = result.get(
        "ids",
        [],
    )

    documents = result.get(
        "documents",
        [],
    )

    metadatas = result.get(
        "metadatas",
        [],
    )

    chunks: list[
        dict[str, Any]
    ] = []

    for index, document_id in enumerate(
        ids
    ):
        metadata = (
            metadatas[index]
            if index < len(metadatas)
            else {}
        )

        document = (
            documents[index]
            if index < len(documents)
            else ""
        )

        metadata = metadata or {}

        if (
            str(
                metadata.get(
                    "source_id",
                    "",
                )
            )
            == source_id
        ):
            chunks.append(
                {
                    "id": document_id,
                    "text": document,
                    "metadata": metadata,
                }
            )

    return chunks


# =============================================================
# END
# =============================================================