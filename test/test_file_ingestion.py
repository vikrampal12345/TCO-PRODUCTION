from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.rag.vectorstore import (
    collection,
)
from backend.services.file_ingestion import (
    TeacherFileIngestionService,
)


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

TEST_PDF = (
    PROJECT_ROOT
    / "data"
    / "documents"
    / "sql_notes.pdf"
)


# ============================================================
# Test Identity
# ============================================================

TEACHER_ID = "teacher-demo"

SCHOOL_ID = "TCO_TEST"

CONVERSATION_ID = "conversation_rag_test"


# ============================================================
# Helper Functions
# ============================================================

def get_all_chunks() -> list[dict[str, Any]]:
    """
    Read all chunks from the current Chroma collection.

    We intentionally fetch everything and filter in Python.
    This keeps the test compatible with the installed Chroma
    version and avoids invalid multi-field `where` syntax.
    """

    result = collection.get(
        include=[
            "documents",
            "metadatas",
        ]
    )

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

    for index, chunk_id in enumerate(
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

        chunks.append(
            {
                "id": chunk_id,
                "text": document,
                "metadata": metadata,
            }
        )

    return chunks


def get_test_scope_chunks() -> list[dict[str, Any]]:
    """
    Return only the chunks created by this test.
    """

    all_chunks = get_all_chunks()

    matched: list[
        dict[str, Any]
    ] = []

    for chunk in all_chunks:

        metadata = chunk.get(
            "metadata",
            {},
        )

        if (
            metadata.get("source_type")
            == "teacher_file"
            and metadata.get("teacher_id")
            == TEACHER_ID
            and metadata.get("school_id")
            == SCHOOL_ID
            and metadata.get("conversation_id")
            == CONVERSATION_ID
        ):
            matched.append(
                chunk
            )

    return matched


def cleanup_test_scope() -> int:
    """
    Remove only chunks belonging to this test.

    This makes the test repeatable.

    It does NOT delete other Chroma data.
    """

    test_chunks = (
        get_test_scope_chunks()
    )

    if not test_chunks:
        return 0

    ids = [
        chunk["id"]
        for chunk in test_chunks
    ]

    collection.delete(
        ids=ids
    )

    return len(ids)


# ============================================================
# Main Test
# ============================================================

def main() -> None:

    print(
        "\n========================================"
    )

    print(
        "TCO TEACHER FILE → RAG TEST"
    )

    print(
        "========================================"
    )

    print(
        "\nTest file:"
    )

    print(
        TEST_PDF
    )

    # --------------------------------------------------------
    # Clean previous test data
    # --------------------------------------------------------

    removed = cleanup_test_scope()

    print(
        "\nOld test chunks removed:",
        removed,
    )

    # --------------------------------------------------------
    # Initialize service
    # --------------------------------------------------------

    service = (
        TeacherFileIngestionService()
    )

    before_count = (
        collection.count()
    )

    print(
        "\nChroma count before:",
        before_count,
    )

    # --------------------------------------------------------
    # First ingestion
    # --------------------------------------------------------

    print(
        "\n----------------------------------------"
    )

    print(
        "FIRST INGESTION"
    )

    print(
        "----------------------------------------"
    )

    result = service.ingest(
        TEST_PDF,
        teacher_id=TEACHER_ID,
        school_id=SCHOOL_ID,
        conversation_id=CONVERSATION_ID,
    )

    print(
        "\nIngestion result:"
    )

    print(
        result
    )

    # --------------------------------------------------------
    # Validate ingestion result
    # --------------------------------------------------------

    assert result["success"] is True, (
        "File ingestion failed."
    )

    assert result["source_type"] == (
        "teacher_file"
    )

    assert result["teacher_id"] == (
        TEACHER_ID
    )

    assert result["school_id"] == (
        SCHOOL_ID
    )

    assert result["conversation_id"] == (
        CONVERSATION_ID
    )

    assert result["document_count"] > 0, (
        "No documents were loaded."
    )

    assert result["chunk_count"] > 0, (
        "No chunks were created."
    )

    # --------------------------------------------------------
    # Validate Chroma count
    # --------------------------------------------------------

    after_count = (
        collection.count()
    )

    print(
        "\nChroma count after:",
        after_count,
    )

    expected_count = (
        before_count
        + result["chunk_count"]
    )

    assert after_count == expected_count, (
        "Unexpected Chroma count after ingestion. "
        f"Expected {expected_count}, "
        f"got {after_count}."
    )

    # --------------------------------------------------------
    # Find stored teacher-file chunks
    # --------------------------------------------------------

    stored = (
        get_test_scope_chunks()
    )

    assert stored, (
        "No teacher-file chunks found "
        "with expected metadata."
    )

    assert len(stored) == (
        result["chunk_count"]
    ), (
        "Stored chunk count does not match "
        "ingestion chunk count."
    )

    print(
        "\nStored teacher-file chunks:",
        len(stored),
    )

    # --------------------------------------------------------
    # Validate metadata
    # --------------------------------------------------------

    for chunk in stored:

        metadata = chunk.get(
            "metadata",
            {},
        )

        assert metadata.get(
            "source_type"
        ) == "teacher_file"

        assert metadata.get(
            "teacher_id"
        ) == TEACHER_ID

        assert metadata.get(
            "school_id"
        ) == SCHOOL_ID

        assert metadata.get(
            "conversation_id"
        ) == CONVERSATION_ID

    print(
        "\nMetadata isolation test passed."
    )

    # --------------------------------------------------------
    # Show first chunk
    # --------------------------------------------------------

    print(
        "\nFirst chunk metadata:"
    )

    print(
        stored[0]["metadata"]
    )

    print(
        "\nFirst chunk preview:"
    )

    print(
        stored[0]["text"][:500]
    )

    # --------------------------------------------------------
    # Re-ingestion test
    # --------------------------------------------------------

    print(
        "\n----------------------------------------"
    )

    print(
        "RE-INGESTION / DUPLICATE TEST"
    )

    print(
        "----------------------------------------"
    )

    count_before_reingest = (
        collection.count()
    )

    second_result = service.ingest(
        TEST_PDF,
        teacher_id=TEACHER_ID,
        school_id=SCHOOL_ID,
        conversation_id=CONVERSATION_ID,
    )

    count_after_reingest = (
        collection.count()
    )

    print(
        "\nFirst ingestion chunks:",
        result["chunk_count"],
    )

    print(
        "Second ingestion chunks:",
        second_result["chunk_count"],
    )

    print(
        "Chroma count before re-ingestion:",
        count_before_reingest,
    )

    print(
        "Chroma count after re-ingestion:",
        count_after_reingest,
    )

    assert second_result["success"] is True

    assert second_result["chunk_count"] == (
        result["chunk_count"]
    )

    # Same deterministic chunk IDs + Chroma upsert
    # should NOT create duplicate chunks.
    assert (
        count_after_reingest
        == count_before_reingest
    ), (
        "Re-ingestion created duplicate "
        "Chroma chunks."
    )

    stored_after_reingestion = (
        get_test_scope_chunks()
    )

    assert len(
        stored_after_reingestion
    ) == result["chunk_count"], (
        "Teacher-file chunk count increased "
        "after re-ingestion."
    )

    print(
        "\nDuplicate test passed."
    )

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    print(
        "\n========================================"
    )

    print(
        "TEACHER FILE → RAG TEST PASSED"
    )

    print(
        "========================================"
    )


if __name__ == "__main__":
    main()