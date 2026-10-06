from pathlib import Path

from backend.rag import loader
from backend.rag.vectorstore import (
    collection,
    create_chunks,
    get_collection_count,
    get_source_id_chunks,
    index_file,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PDF_PATH = (
    PROJECT_ROOT
    / "data"
    / "documents"
    / "sql_notes.pdf"
)

TEST_SOURCE_ID = (
    "vectorstore_test_sql_notes_pdf"
)


def test_chunking() -> None:
    """
    Test the chunking function independently.
    """

    text = (
        "SQL is a language used to work with "
        "relational databases. "
        * 100
    )

    chunks = create_chunks(
        text,
        chunk_size=800,
        chunk_overlap=100,
    )

    assert chunks, (
        "Chunking returned zero chunks."
    )

    for chunk in chunks:
        assert chunk.strip(), (
            "An empty chunk was created."
        )

    print(
        "Chunking test passed."
    )

    print(
        "Chunks created:",
        len(chunks),
    )


def test_pdf_loading() -> None:
    """
    Confirm that the loader returns valid
    document structures for the SQL PDF.
    """

    documents = loader.load_file(
        str(PDF_PATH)
    )

    assert documents, (
        "Loader returned zero documents."
    )

    print(
        "Documents loaded:",
        len(documents),
    )

    for document in documents:

        assert "text" in document

        assert "metadata" in document

        assert document["text"].strip()

    print(
        "Document structure test passed."
    )


def test_collection_exists() -> None:
    """
    Verify the Chroma collection exists.
    """

    assert collection is not None

    print(
        "Chroma collection:"
    )

    print(
        collection.name
    )


def test_indexing() -> None:
    """
    Index the SQL PDF using a deterministic test source_id
    and verify exactly those chunks through source_id lookup.
    """

    source = str(
        PDF_PATH
    )

    before_count = (
        get_collection_count()
    )

    print(
        "\nChroma count before:",
        before_count,
    )

    chunk_count = index_file(
        source,
        loader=loader,
        source_id=TEST_SOURCE_ID,
    )

    assert chunk_count > 0, (
        "No chunks were indexed."
    )

    print(
        "Chunks indexed:",
        chunk_count,
    )

    after_count = (
        get_collection_count()
    )

    print(
        "Chroma count after:",
        after_count,
    )

    source_chunks = (
        get_source_id_chunks(
            TEST_SOURCE_ID
        )
    )

    assert source_chunks, (
        "No chunks found for the indexed source_id."
    )

    print(
        "Stored source-id chunks:",
        len(source_chunks),
    )

    assert len(source_chunks) == (
        chunk_count
    ), (
        "Indexed chunk count and stored "
        "source-id chunk count do not match."
    )

    for chunk in source_chunks:

        assert chunk.get("id"), (
            "Stored chunk is missing an ID."
        )

        assert chunk.get("text", "").strip(), (
            "Stored chunk contains empty text."
        )

        metadata = chunk.get(
            "metadata",
            {},
        )

        assert metadata.get(
            "source_id"
        ) == TEST_SOURCE_ID, (
            "Stored chunk has an unexpected source_id."
        )

    print(
        "Source ID metadata test passed."
    )

    print(
        "\nFirst stored chunk:"
    )

    print(
        source_chunks[0]["text"][:500]
    )


def main() -> None:

    print(
        "\n========================================"
    )

    print(
        "TCO VECTOR STORE TEST"
    )

    print(
        "========================================"
    )

    print(
        "\nPDF:"
    )

    print(
        PDF_PATH
    )

    print(
        "\nTest source ID:"
    )

    print(
        TEST_SOURCE_ID
    )

    test_chunking()

    print(
        "\n----------------------------------------"
    )

    test_pdf_loading()

    print(
        "\n----------------------------------------"
    )

    test_collection_exists()

    print(
        "\n----------------------------------------"
    )

    test_indexing()

    print(
        "\n========================================"
    )

    print(
        "VECTOR STORE TEST PASSED"
    )

    print(
        "========================================"
    )


if __name__ == "__main__":
    main()