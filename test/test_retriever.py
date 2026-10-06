from pathlib import Path

from backend.rag.retriever import (
    retrieve_context,
    retrieve_context_with_scores,
    retrieve_documents,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

QUERY = (
    "What is the purpose of the WHERE clause in SQL?"
)

TOP_K = 5

SIMILARITY_THRESHOLD = 0.30


def build_references(
    results: list[dict],
) -> list[str]:
    """
    Build human-readable source references from
    scored retrieval results.
    """

    references: list[str] = []

    for result in results:

        metadata = result.get(
            "metadata",
            {},
        )

        if not isinstance(
            metadata,
            dict,
        ):
            metadata = {}

        source = str(
            metadata.get(
                "source",
                "",
            )
            or ""
        ).strip()

        if not source:
            continue

        page = metadata.get(
            "page",
            "",
        )

        chunk = metadata.get(
            "chunk",
            metadata.get(
                "chunk_in_document",
                "",
            ),
        )

        reference = (
            f"{source}"
            f" - page {page}"
            f" - chunk {chunk}"
        )

        references.append(
            reference
        )

    return references


def test_retrieve_documents() -> list[dict]:
    """
    Test semantic document retrieval.
    """

    print(
        "\n----------------------------------------"
    )

    print(
        "TEST 1: RETRIEVE DOCUMENTS"
    )

    print(
        "----------------------------------------"
    )

    results = retrieve_documents(
        query=QUERY,
        top_k=TOP_K,
        similarity_threshold=SIMILARITY_THRESHOLD,
    )

    assert results, (
        "Retriever returned zero documents."
    )

    assert len(results) <= TOP_K, (
        "Retriever returned more results "
        "than the requested top_k."
    )

    print(
        "\nDocuments retrieved:",
        len(results),
    )

    for index, result in enumerate(
        results,
        start=1,
    ):

        print(
            f"\nResult {index}"
        )

        similarity = result.get(
            "similarity",
            None,
        )

        if similarity is not None:

            try:
                print(
                    "Similarity:",
                    f"{float(similarity):.4f}",
                )
            except (
                TypeError,
                ValueError,
            ):
                print(
                    "Similarity:",
                    similarity,
                )

        metadata = result.get(
            "metadata",
            {},
        )

        print(
            "Metadata:",
            metadata,
        )

        text = str(
            result.get(
                "text",
                "",
            )
            or ""
        )

        print(
            "Text preview:"
        )

        print(
            text[:500]
        )

        assert text.strip(), (
            "Retrieved result contains empty text."
        )

        assert isinstance(
            metadata,
            dict,
        ), (
            "Retrieved metadata must be a dictionary."
        )

    print(
        "\nDocument retrieval test passed."
    )

    return results


def test_build_context() -> tuple[
    str,
    list[dict],
]:
    """
    Test the current retrieve_context() contract.

    IMPORTANT:
    retrieve_context() returns ONE string.
    It does not return (context, references).
    """

    print(
        "\n----------------------------------------"
    )

    print(
        "TEST 2: BUILD RAG CONTEXT"
    )

    print(
        "----------------------------------------"
    )

    context = retrieve_context(
        query=QUERY,
        top_k=TOP_K,
        similarity_threshold=SIMILARITY_THRESHOLD,
    )

    assert isinstance(
        context,
        str,
    ), (
        "retrieve_context() must return a string."
    )

    assert context.strip(), (
        "retrieve_context() returned empty context."
    )

    print(
        "\nContext generated successfully."
    )

    print(
        "\nContext preview:"
    )

    print(
        context[:2500]
    )

    scored_results = (
        retrieve_context_with_scores(
            query=QUERY,
            top_k=TOP_K,
            similarity_threshold=SIMILARITY_THRESHOLD,
        )
    )

    assert scored_results, (
        "retrieve_context_with_scores() "
        "returned zero results."
    )

    references = build_references(
        scored_results
    )

    assert references, (
        "No source references were built "
        "from scored retrieval results."
    )

    print(
        "\nSource References:"
    )

    for reference in references:
        print(
            f" - {reference}"
        )

    print(
        "\nRAG context test passed."
    )

    return (
        context,
        scored_results,
    )


def test_retrieval_with_scores(
    results: list[dict],
) -> None:
    """
    Test scored retrieval and verify that
    result structure contains usable data.
    """

    print(
        "\n----------------------------------------"
    )

    print(
        "TEST 3: RETRIEVAL WITH SCORES"
    )

    print(
        "----------------------------------------"
    )

    scored_results = (
        retrieve_context_with_scores(
            query=QUERY,
            top_k=TOP_K,
            similarity_threshold=SIMILARITY_THRESHOLD,
        )
    )

    assert scored_results, (
        "Scored retrieval returned zero results."
    )

    assert len(scored_results) <= TOP_K, (
        "Scored retrieval returned more results "
        "than requested."
    )

    print(
        "\nResult count:",
        len(scored_results),
    )

    for result in scored_results:

        metadata = result.get(
            "metadata",
            {},
        )

        similarity = result.get(
            "similarity",
            None,
        )

        source = ""

        if isinstance(
            metadata,
            dict,
        ):
            source = str(
                metadata.get(
                    "source",
                    "",
                )
                or ""
            ).strip()

        print()

        print(
            "Reference:",
            (
                f"{source} - page "
                f"{metadata.get('page', '')} "
                f"- chunk "
                f"{metadata.get(
                    'chunk',
                    metadata.get(
                        'chunk_in_document',
                        '',
                    ),
                )}"
            ),
        )

        print(
            "Similarity:",
            similarity,
        )

        assert isinstance(
            metadata,
            dict,
        ), (
            "Result metadata must be a dictionary."
        )

        assert source, (
            "Retrieved result is missing "
            "source metadata."
        )

        assert similarity is not None, (
            "Retrieved result is missing similarity."
        )

    print(
        "\nScored retrieval test passed."
    )


def main() -> None:

    print(
        "\n========================================"
    )

    print(
        "TCO RETRIEVER TEST"
    )

    print(
        "========================================"
    )

    print(
        "\nQuery:"
    )

    print(
        QUERY
    )

    document_results = (
        test_retrieve_documents()
    )

    test_build_context()

    test_retrieval_with_scores(
        document_results
    )

    print(
        "\n========================================"
    )

    print(
        "RETRIEVER TEST PASSED"
    )

    print(
        "========================================"
    )


if __name__ == "__main__":
    main()