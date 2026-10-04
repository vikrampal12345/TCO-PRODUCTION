from __future__ import annotations

from pathlib import Path

from backend.rag.retriever import (
    retrieve_teacher_documents,
)
from backend.services.file_ingestion import (
    TeacherFileIngestionService,
)
from backend.rag.vectorstore import collection


TEST_FILE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "documents"
    / "sql_notes.pdf"
)

SCHOOL_ID = "TCO_SCOPE_TEST"

TEACHER_A = "teacher-scope-A"
TEACHER_B = "teacher-scope-B"

CONVERSATION_A = "conversation-scope-A"
CONVERSATION_B = "conversation-scope-B"


def cleanup_test_scope() -> int:
    """
    Remove only chunks created by this test.

    Existing unrelated RAG data is preserved.
    """
    result = collection.get(
        include=["metadatas"]
    )

    ids = result.get("ids", [])
    metadatas = result.get("metadatas", [])

    ids_to_delete: list[str] = []

    for index, metadata in enumerate(metadatas):
        if index >= len(ids):
            break

        metadata = metadata or {}

        teacher_id = metadata.get("teacher_id")
        school_id = metadata.get("school_id")
        source_type = metadata.get("source_type")

        if (
            school_id == SCHOOL_ID
            and source_type == "teacher_file"
            and teacher_id in {TEACHER_A, TEACHER_B}
        ):
            ids_to_delete.append(ids[index])

    if ids_to_delete:
        collection.delete(
            ids=ids_to_delete
        )

    return len(ids_to_delete)


def assert_all_match(
    results: list[dict],
    *,
    teacher_id: str,
    school_id: str,
) -> None:
    """
    Verify every retrieved chunk belongs to the expected scope.
    """
    assert results, (
        "Expected retrieval results, but got none."
    )

    for result in results:
        metadata = result["metadata"]

        assert metadata.get("teacher_id") == teacher_id, (
            "Teacher isolation failed.\n"
            f"Expected teacher: {teacher_id}\n"
            f"Got metadata: {metadata}"
        )

        assert metadata.get("school_id") == school_id, (
            "School isolation failed.\n"
            f"Expected school: {school_id}\n"
            f"Got metadata: {metadata}"
        )


def main() -> None:
    print()
    print("=" * 40)
    print("TCO RETRIEVAL SCOPE TEST")
    print("=" * 40)

    if not TEST_FILE.exists():
        raise FileNotFoundError(
            f"Test file not found: {TEST_FILE}"
        )

    print()
    print(f"Test file:")
    print(TEST_FILE)

    removed = cleanup_test_scope()

    print()
    print(f"Old scope-test chunks removed: {removed}")

    ingestion_service = TeacherFileIngestionService()

    # ---------------------------------------------------------
    # INGEST FOR TEACHER A
    # ---------------------------------------------------------
    print()
    print("-" * 40)
    print("INGESTING TEACHER A MATERIAL")
    print("-" * 40)

    result_a = ingestion_service.ingest(
        TEST_FILE,
        teacher_id=TEACHER_A,
        school_id=SCHOOL_ID,
        conversation_id=CONVERSATION_A,
    )

    print()
    print("Teacher A ingestion:")
    print(result_a)

    assert result_a["success"] is True
    assert result_a["chunk_count"] > 0

    # ---------------------------------------------------------
    # INGEST FOR TEACHER B
    # ---------------------------------------------------------
    print()
    print("-" * 40)
    print("INGESTING TEACHER B MATERIAL")
    print("-" * 40)

    result_b = ingestion_service.ingest(
        TEST_FILE,
        teacher_id=TEACHER_B,
        school_id=SCHOOL_ID,
        conversation_id=CONVERSATION_B,
    )

    print()
    print("Teacher B ingestion:")
    print(result_b)

    assert result_b["success"] is True
    assert result_b["chunk_count"] > 0

    # ---------------------------------------------------------
    # COUNT SCOPED CHUNKS
    # ---------------------------------------------------------
    stored = collection.get(
        include=["metadatas"]
    )

    stored_ids = stored.get("ids", [])
    stored_metadatas = stored.get("metadatas", [])

    teacher_a_count = 0
    teacher_b_count = 0

    for index, metadata in enumerate(stored_metadatas):
        if index >= len(stored_ids):
            break

        metadata = metadata or {}

        if (
            metadata.get("teacher_id") == TEACHER_A
            and metadata.get("school_id") == SCHOOL_ID
            and metadata.get("source_type") == "teacher_file"
        ):
            teacher_a_count += 1

        if (
            metadata.get("teacher_id") == TEACHER_B
            and metadata.get("school_id") == SCHOOL_ID
            and metadata.get("source_type") == "teacher_file"
        ):
            teacher_b_count += 1

    print()
    print("-" * 40)
    print("STORED SCOPE DATA")
    print("-" * 40)

    print(f"Teacher A chunks: {teacher_a_count}")
    print(f"Teacher B chunks: {teacher_b_count}")

    assert teacher_a_count == result_a["chunk_count"]
    assert teacher_b_count == result_b["chunk_count"]

    print("Stored scope metadata verified.")

    # ---------------------------------------------------------
    # RETRIEVE AS TEACHER A
    # ---------------------------------------------------------
    print()
    print("-" * 40)
    print("RETRIEVAL AS TEACHER A")
    print("-" * 40)

    results_a = retrieve_teacher_documents(
        "What is the purpose of the WHERE clause in SQL?",
        teacher_id=TEACHER_A,
        school_id=SCHOOL_ID,
        top_k=5,
        similarity_threshold=0.30,
    )

    print()
    print(f"Teacher A retrieval results: {len(results_a)}")

    for result in results_a:
        print(
            f"similarity={result['similarity']:.4f} | "
            f"teacher={result['metadata'].get('teacher_id')} | "
            f"school={result['metadata'].get('school_id')} | "
            f"file={result['metadata'].get('file_name')}"
        )

    assert_all_match(
        results_a,
        teacher_id=TEACHER_A,
        school_id=SCHOOL_ID,
    )

    print()
    print("Teacher A isolation test passed.")

    # ---------------------------------------------------------
    # RETRIEVE AS TEACHER B
    # ---------------------------------------------------------
    print()
    print("-" * 40)
    print("RETRIEVAL AS TEACHER B")
    print("-" * 40)

    results_b = retrieve_teacher_documents(
        "What is the purpose of the WHERE clause in SQL?",
        teacher_id=TEACHER_B,
        school_id=SCHOOL_ID,
        top_k=5,
        similarity_threshold=0.30,
    )

    print()
    print(f"Teacher B retrieval results: {len(results_b)}")

    for result in results_b:
        print(
            f"similarity={result['similarity']:.4f} | "
            f"teacher={result['metadata'].get('teacher_id')} | "
            f"school={result['metadata'].get('school_id')} | "
            f"file={result['metadata'].get('file_name')}"
        )

    assert_all_match(
        results_b,
        teacher_id=TEACHER_B,
        school_id=SCHOOL_ID,
    )

    print()
    print("Teacher B isolation test passed.")

    # ---------------------------------------------------------
    # CROSS-TEACHER PROTECTION
    # ---------------------------------------------------------
    print()
    print("-" * 40)
    print("CROSS-TEACHER PROTECTION TEST")
    print("-" * 40)

    for result in results_a:
        assert (
            result["metadata"].get("teacher_id")
            != TEACHER_B
        ), "Teacher A received Teacher B data."

    for result in results_b:
        assert (
            result["metadata"].get("teacher_id")
            != TEACHER_A
        ), "Teacher B received Teacher A data."

    print("Cross-teacher leakage test passed.")

    # ---------------------------------------------------------
    # CONVERSATION SCOPE
    # ---------------------------------------------------------
    print()
    print("-" * 40)
    print("CONVERSATION SCOPE TEST")
    print("-" * 40)

    conversation_results = retrieve_teacher_documents(
        "What is SQL?",
        teacher_id=TEACHER_A,
        school_id=SCHOOL_ID,
        conversation_id=CONVERSATION_A,
        top_k=5,
        similarity_threshold=0.30,
    )

    assert conversation_results, (
        "Expected conversation-scoped results."
    )

    for result in conversation_results:
        metadata = result["metadata"]

        assert metadata.get("teacher_id") == TEACHER_A
        assert metadata.get("school_id") == SCHOOL_ID
        assert (
            metadata.get("conversation_id")
            == CONVERSATION_A
        )

        assert (
            metadata.get("conversation_id")
            != CONVERSATION_B
        )

    print("Conversation isolation test passed.")

    print()
    print("=" * 40)
    print("RETRIEVAL SCOPE TEST PASSED")
    print("=" * 40)
    print()


if __name__ == "__main__":
    main()