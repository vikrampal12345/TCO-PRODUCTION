from __future__ import annotations

from typing import Any
import logging

from backend.rag.vectorstore import collection, embedding_model


DEFAULT_TOP_K = 5
DEFAULT_SIMILARITY_THRESHOLD = 0.30
MAX_RETRIEVED_CONTEXT_CHARACTERS = 12000

logger = logging.getLogger(__name__)


class RetrieverError(Exception):
    """Raised when retrieval fails."""


def _distance_to_similarity(distance: float) -> float:
    """
    Convert Chroma distance to a similarity score.

    For the current embedding setup:
        similarity = 1 - distance / 2

    The result is clamped to [-1, 1].
    """
    try:
        similarity = 1.0 - (float(distance) / 2.0)
    except (TypeError, ValueError):
        return 0.0

    return max(-1.0, min(1.0, similarity))


def _build_metadata_filter(
    *,
    teacher_id: str | None = None,
    school_id: str | None = None,
    conversation_id: str | None = None,
    source_type: str | None = None,
    source: str | None = None,
) -> dict[str, Any] | None:
    """
    Build a Chroma metadata filter.

    Multiple conditions are combined using $and so that
    teacher/school/conversation scope can be enforced together.
    """
    conditions: list[dict[str, Any]] = []

    if teacher_id is not None:
        teacher_id = teacher_id.strip()
        if teacher_id:
            conditions.append(
                {"teacher_id": {"$eq": teacher_id}}
            )

    if school_id is not None:
        school_id = school_id.strip()
        if school_id:
            conditions.append(
                {"school_id": {"$eq": school_id}}
            )

    if conversation_id is not None:
        conversation_id = conversation_id.strip()
        if conversation_id:
            conditions.append(
                {"conversation_id": {"$eq": conversation_id}}
            )

    if source_type is not None:
        source_type = source_type.strip()
        if source_type:
            conditions.append(
                {"source_type": {"$eq": source_type}}
            )

    if source is not None:
        source = source.strip()
        if source:
            conditions.append(
                {"source": {"$eq": source}}
            )

    if not conditions:
        return None

    if len(conditions) == 1:
        return conditions[0]

    return {
        "$and": conditions
    }


def _validate_inputs(
    query: str,
    top_k: int,
    similarity_threshold: float,
) -> None:
    """Validate retrieval inputs."""
    if not isinstance(query, str) or not query.strip():
        raise RetrieverError("Query must be a non-empty string.")

    if top_k <= 0:
        raise RetrieverError("top_k must be greater than 0.")

    if not 0.0 <= similarity_threshold <= 1.0:
        raise RetrieverError(
            "similarity_threshold must be between 0.0 and 1.0."
        )


def retrieve_documents(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    *,
    teacher_id: str | None = None,
    school_id: str | None = None,
    conversation_id: str | None = None,
    source_type: str | None = None,
    source: str | None = None,
) -> list[dict[str, Any]]:
    """
    Retrieve relevant documents from Chroma.

    Optional metadata filters provide retrieval scope.

    Example:

        retrieve_documents(
            "What is SQL?",
            teacher_id="teacher-a",
            school_id="school-1",
        )

    This will only retrieve chunks matching BOTH:
        teacher_id = teacher-a
        school_id = school-1
    """
    _validate_inputs(
        query,
        top_k,
        similarity_threshold,
    )

    try:
        collection_count = collection.count()
    except Exception as exc:
        raise RetrieverError(
            f"Could not read vector store count: {exc}"
        ) from exc

    if collection_count == 0:
        return []

    try:
        query_embedding = embedding_model.encode(
            query.strip(),
            normalize_embeddings=True,
        )

        where = _build_metadata_filter(
            teacher_id=teacher_id,
            school_id=school_id,
            conversation_id=conversation_id,
            source_type=source_type,
            source=source,
        )

        query_kwargs: dict[str, Any] = {
            "query_embeddings": [
                query_embedding.tolist()
            ],
            "n_results": min(top_k, collection_count),
            "include": [
                "documents",
                "metadatas",
                "distances",
            ],
        }

        if where is not None:
            query_kwargs["where"] = where

        result = collection.query(**query_kwargs)

    except Exception as exc:
        raise RetrieverError(
            f"Vector retrieval failed: {exc}"
        ) from exc

    documents = result.get("documents", [[]])
    metadatas = result.get("metadatas", [[]])
    distances = result.get("distances", [[]])
    ids = result.get("ids", [[]])

    if not documents:
        return []

    raw_documents = documents[0] if documents[0] else []
    raw_metadatas = metadatas[0] if metadatas and metadatas[0] else []
    raw_distances = distances[0] if distances and distances[0] else []
    raw_ids = ids[0] if ids and ids[0] else []

    retrieved: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for index, text in enumerate(raw_documents):
        document_id = (
            str(raw_ids[index])
            if index < len(raw_ids)
            else f"retrieved-{index}"
        )

        if document_id in seen_ids:
            continue

        seen_ids.add(document_id)

        metadata = (
            dict(raw_metadatas[index])
            if index < len(raw_metadatas)
            and raw_metadatas[index]
            else {}
        )

        distance = (
            float(raw_distances[index])
            if index < len(raw_distances)
            else 0.0
        )

        similarity = _distance_to_similarity(distance)

        if similarity < similarity_threshold:
            continue

        retrieved.append(
            {
                "id": document_id,
                "text": str(text),
                "metadata": metadata,
                "distance": distance,
                "similarity": similarity,
            }
        )

    retrieved.sort(
        key=lambda item: item["similarity"],
        reverse=True,
    )

    return retrieved


def retrieve_context(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    *,
    teacher_id: str | None = None,
    school_id: str | None = None,
    conversation_id: str | None = None,
    source_type: str | None = None,
    source: str | None = None,
) -> str:
    """
    Return retrieved text as a single context string.

    This function supports the same scope filters as
    retrieve_documents().
    """
    results = retrieve_documents(
        query,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
        teacher_id=teacher_id,
        school_id=school_id,
        conversation_id=conversation_id,
        source_type=source_type,
        source=source,
    )

    if not results:
        return ""

    context_parts: list[str] = []
    total_characters = 0

    for index, result in enumerate(results, start=1):
        metadata = result.get("metadata", {})

        source_name = metadata.get(
            "file_name",
            metadata.get("source", "unknown"),
        )

        page = metadata.get("page")

        source_label = str(source_name)

        if page is not None:
            source_label += f", page {page}"

        block = (
            f"[Source {index}: {source_label}]\n"
            f"{result['text']}"
        )
        separator_length = 2 if context_parts else 0
        remaining = (
            MAX_RETRIEVED_CONTEXT_CHARACTERS
            - total_characters
            - separator_length
        )
        if remaining <= 0:
            break
        context_parts.append(block[:remaining])
        total_characters += separator_length + min(len(block), remaining)

    logger.info(
        "RAG context assembled: chunks=%d chars=%d query_chars=%d",
        len(context_parts),
        total_characters,
        len(query),
    )

    return "\n\n".join(context_parts)


def retrieve_context_with_scores(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    *,
    teacher_id: str | None = None,
    school_id: str | None = None,
    conversation_id: str | None = None,
    source_type: str | None = None,
    source: str | None = None,
) -> list[dict[str, Any]]:
    """
    Return retrieved chunks including similarity scores.

    Useful for debugging and testing retrieval quality.
    """
    return retrieve_documents(
        query,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
        teacher_id=teacher_id,
        school_id=school_id,
        conversation_id=conversation_id,
        source_type=source_type,
        source=source,
    )


def retrieve_teacher_documents(
    query: str,
    *,
    teacher_id: str,
    school_id: str,
    top_k: int = DEFAULT_TOP_K,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    conversation_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Strict teacher-scoped retrieval.

    teacher_id and school_id are mandatory.

    This is the function Work Mode should normally use when
    retrieving teacher-private material.
    """
    if not teacher_id.strip():
        raise RetrieverError("teacher_id is required.")

    if not school_id.strip():
        raise RetrieverError("school_id is required.")

    return retrieve_documents(
        query,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
        teacher_id=teacher_id,
        school_id=school_id,
        conversation_id=conversation_id,
    )


def retrieve_teacher_context(
    query: str,
    *,
    teacher_id: str,
    school_id: str,
    top_k: int = DEFAULT_TOP_K,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    conversation_id: str | None = None,
) -> str:
    """
    Strict teacher-scoped context retrieval.

    Work Mode can use this to retrieve private teacher material
    without accidentally mixing another teacher's material.
    """
    if not teacher_id.strip():
        raise RetrieverError("teacher_id is required.")

    if not school_id.strip():
        raise RetrieverError("school_id is required.")

    return retrieve_context(
        query,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
        teacher_id=teacher_id,
        school_id=school_id,
        conversation_id=conversation_id,
    )


def retrieve_source_context(
    query: str,
    *,
    source: str,
    top_k: int = DEFAULT_TOP_K,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> str:
    """
    Retrieve context only from one exact source path.
    """
    if not source.strip():
        raise RetrieverError("source is required.")

    return retrieve_context(
        query,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
        source=source,
    )