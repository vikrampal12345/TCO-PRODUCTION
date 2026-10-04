from pathlib import Path

from backend.rag.loader import load_file
from backend.rag.vectorstore import (
    collection,
    create_chunks,
    get_collection_count,
    get_source_chunks,
    index_file,
)


PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

PDF_PATH = (
    PROJECT_ROOT
    / "data"
    / "documents"
    / "sql_notes.pdf"
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
    Confirm that the loader and vectorstore
    receive the expected PDF documents.
    """

    documents = load_file(
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


def test_indexing() -> None:
    """
    Index the SQL PDF and verify that its
    chunks exist in ChromaDB.
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
        source
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
        get_source_chunks(
            source
        )
    )

    assert source_chunks, (
        "No chunks found for the indexed source."
    )

    assert len(source_chunks) == (
        chunk_count
    ), (
        "Indexed chunk count and stored "
        "source chunk count do not match."
    )

    print(
        "Stored source chunks:",
        len(source_chunks),
    )

    print(
        "\nFirst stored chunk:"
    )

    print(
        source_chunks[0]["text"][:500]
    )


def test_collection_exists() -> None:
    """
    Verify the Chroma collection itself exists.
    """

    assert collection is not None

    print(
        "Chroma collection:"
    )

    print(
        collection.name
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