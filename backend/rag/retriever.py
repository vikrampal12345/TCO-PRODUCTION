from backend.rag.vectorstore import (
    collection,
    embedding_model,
)


# ============================================================
# Configuration
# ============================================================

DEFAULT_TOP_K = 5

# Conservative MVP threshold.
# Higher similarity = more relevant.
SIMILARITY_THRESHOLD = 0.30


# ============================================================
# Distance → Cosine Similarity
# ============================================================

def distance_to_similarity(distance: float) -> float:
    """
    Convert squared L2 distance between normalized embeddings
    into cosine similarity.

    For normalized vectors:

        squared_L2 = 2 - 2 * cosine_similarity

    Therefore:

        cosine_similarity = 1 - squared_L2 / 2
    """

    return 1.0 - (distance / 2.0)


# ============================================================
# Retrieve Documents
# ============================================================

def retrieve_documents(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    similarity_threshold: float = SIMILARITY_THRESHOLD,
) -> list[dict]:
    """
    Retrieve relevant document chunks from Chroma.

    Only results meeting the similarity threshold are returned.
    """

    if not query or not query.strip():
        return []

    query_embedding = embedding_model.encode(
        query,
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    documents = results.get(
        "documents",
        [[]],
    )[0]

    metadatas = results.get(
        "metadatas",
        [[]],
    )[0]

    distances = results.get(
        "distances",
        [[]],
    )[0]

    retrieved = []

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances,
    ):

        similarity = distance_to_similarity(
            float(distance)
        )

        # Ignore weakly related results.
        if similarity < similarity_threshold:
            continue

        retrieved.append(
            {
                "text": document,
                "metadata": metadata,
                "distance": float(distance),
                "similarity": similarity,
            }
        )

    return retrieved


# ============================================================
# Build RAG Context
# ============================================================

def retrieve_context(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    similarity_threshold: float = SIMILARITY_THRESHOLD,
) -> tuple[str, list[str]]:
    """
    Retrieve relevant chunks and prepare context
    for the Assessment Agent.

    Returns:
        context:
            Combined relevant text.

        source_references:
            Actual source/page/chunk references.
    """

    results = retrieve_documents(
        query=query,
        top_k=top_k,
        similarity_threshold=similarity_threshold,
    )

    if not results:
        return "", []

    context_parts = []
    source_references = []

    for index, result in enumerate(
        results,
        start=1,
    ):

        text = result["text"]
        metadata = result["metadata"]

        source = metadata.get(
            "source",
            "unknown",
        )

        page = metadata.get(
            "page",
            "unknown",
        )

        chunk = metadata.get(
            "chunk"
        )

        if chunk is not None:
            reference = (
                f"{source} - page {page} - chunk {chunk}"
            )
        else:
            reference = (
                f"{source} - page {page}"
            )

        context_parts.append(
            f"[Source {index}: {reference}]\n"
            f"{text}"
        )

        source_references.append(
            reference
        )

    context = "\n\n".join(
        context_parts
    )

    return context, source_references