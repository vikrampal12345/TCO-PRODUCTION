from backend.rag.retriever import (
    retrieve_context,
    retrieve_context_with_scores,
    retrieve_documents,
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

    query = (
        "What is the purpose of the WHERE "
        "clause in SQL?"
    )

    print(
        "\nQuery:"
    )

    print(
        query
    )

    # ========================================================
    # Test 1 — Raw Document Retrieval
    # ========================================================

    print(
        "\n----------------------------------------"
    )

    print(
        "TEST 1: RETRIEVE DOCUMENTS"
    )

    print(
        "----------------------------------------"
    )

    documents = retrieve_documents(
        query=query,
        top_k=5,
        similarity_threshold=0.30,
    )

    if not documents:
        raise RuntimeError(
            "Retriever returned no documents."
        )

    print(
        "\nDocuments retrieved:",
        len(documents),
    )

    for index, document in enumerate(
        documents,
        start=1,
    ):

        print(
            f"\nResult {index}"
        )

        print(
            "Similarity:",
            round(
                document["similarity"],
                4,
            ),
        )

        print(
            "Metadata:",
            document["metadata"],
        )

        print(
            "Text preview:"
        )

        print(
            document["text"][:300]
        )

    # ========================================================
    # Test 2 — RAG Context
    # ========================================================

    print(
        "\n----------------------------------------"
    )

    print(
        "TEST 2: BUILD RAG CONTEXT"
    )

    print(
        "----------------------------------------"
    )

    context, references = retrieve_context(
        query=query,
        top_k=5,
        similarity_threshold=0.30,
    )

    if not context.strip():
        raise RuntimeError(
            "RAG context is empty."
        )

    if not references:
        raise RuntimeError(
            "No source references returned."
        )

    print(
        "\nRAG Context:"
    )

    print(
        context
    )

    print(
        "\nSource References:"
    )

    for reference in references:

        print(
            " -",
            reference,
        )

    # ========================================================
    # Test 3 — Rich Retrieval
    # ========================================================

    print(
        "\n----------------------------------------"
    )

    print(
        "TEST 3: RETRIEVAL WITH SCORES"
    )

    print(
        "----------------------------------------"
    )

    rich_result = (
        retrieve_context_with_scores(
            query=query,
            top_k=5,
            similarity_threshold=0.30,
        )
    )

    if not rich_result["results"]:
        raise RuntimeError(
            "Rich retrieval returned no results."
        )

    print(
        "\nResult count:",
        len(
            rich_result["results"]
        ),
    )

    for result in (
        rich_result["results"]
    ):

        print(
            "\nReference:",
            result["reference"],
        )

        print(
            "Similarity:",
            result["similarity"],
        )

    # ========================================================
    # Final
    # ========================================================

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