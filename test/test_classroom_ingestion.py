from __future__ import annotations

from pathlib import Path

from backend.rag.retriever import retrieve_documents
from backend.rag.vectorstore import collection
from backend.services.classroom_ingestion import (
    ClassroomIngestionError,
    ClassroomIngestionService,
)


COURSE_ID = "871538502094"

# MY NOTES UNIT-2 -> Booth Algorithm Step-by-Step Examples.pdf
MATERIAL_ID = "884229212233"

TEACHER_ID = "teacher-classroom-test"
SCHOOL_ID = "TCO_CLASSROOM_TEST"
CONVERSATION_ID = "conversation-classroom-rag-test"


def cleanup_test_scope() -> int:
    """
    Remove only chunks created by this Classroom RAG test.
    Existing unrelated Chroma data is preserved.
    """
    result = collection.get(
        include=["metadatas"]
    )

    ids = result.get(
        "ids",
        [],
    )

    metadatas = result.get(
        "metadatas",
        [],
    )

    ids_to_delete: list[str] = []

    for index, metadata in enumerate(metadatas):
        if index >= len(ids):
            break

        metadata = metadata or {}

        if (
            metadata.get("source_type")
            == "google_classroom"
            and metadata.get("teacher_id")
            == TEACHER_ID
            and metadata.get("school_id")
            == SCHOOL_ID
            and metadata.get("conversation_id")
            == CONVERSATION_ID
        ):
            ids_to_delete.append(
                ids[index]
            )

    if ids_to_delete:
        collection.delete(
            ids=ids_to_delete
        )

    return len(ids_to_delete)


def get_test_chunks() -> list[dict]:
    """
    Return all chunks belonging to this test scope.
    """
    result = collection.get(
        include=["metadatas", "documents"]
    )

    ids = result.get("ids", [])
    metadatas = result.get(
        "metadatas",
        [],
    )
    documents = result.get(
        "documents",
        [],
    )

    chunks: list[dict] = []

    for index, document_id in enumerate(ids):
        metadata = (
            metadatas[index]
            if index < len(metadatas)
            else {}
        )

        text = (
            documents[index]
            if index < len(documents)
            else ""
        )

        if not metadata:
            metadata = {}

        if (
            metadata.get("source_type")
            == "google_classroom"
            and metadata.get("teacher_id")
            == TEACHER_ID
            and metadata.get("school_id")
            == SCHOOL_ID
            and metadata.get("conversation_id")
            == CONVERSATION_ID
        ):
            chunks.append(
                {
                    "id": document_id,
                    "metadata": metadata,
                    "text": text,
                }
            )

    return chunks


def main() -> None:
    print()
    print("=" * 50)
    print("TCO GOOGLE CLASSROOM → RAG TEST")
    print("=" * 50)

    print()
    print(f"Course ID:       {COURSE_ID}")
    print(f"Material ID:     {MATERIAL_ID}")
    print(f"Teacher ID:      {TEACHER_ID}")
    print(f"School ID:       {SCHOOL_ID}")

    # ---------------------------------------------------------
    # CLEAN PREVIOUS TEST DATA
    # ---------------------------------------------------------

    removed = cleanup_test_scope()

    print()
    print(f"Old Classroom test chunks removed: {removed}")

    # ---------------------------------------------------------
    # CREATE SERVICE
    # ---------------------------------------------------------

    service = ClassroomIngestionService()

    # ---------------------------------------------------------
    # FIRST INGESTION
    # ---------------------------------------------------------

    print()
    print("-" * 50)
    print("FIRST CLASSROOM INGESTION")
    print("-" * 50)

    try:
        result = service.ingest_material(
            course_id=COURSE_ID,
            material_id=MATERIAL_ID,
            teacher_id=TEACHER_ID,
            school_id=SCHOOL_ID,
            conversation_id=CONVERSATION_ID,
        )
    except ClassroomIngestionError as exc:
        raise AssertionError(
            f"Classroom ingestion failed: {exc}"
        ) from exc

    print()
    print("Ingestion result:")
    print(result)

    assert result["success"] is True
    assert result["source_type"] == "google_classroom"
    assert result["course_id"] == COURSE_ID
    assert result["material_id"] == MATERIAL_ID
    assert result["teacher_id"] == TEACHER_ID
    assert result["school_id"] == SCHOOL_ID
    assert result["conversation_id"] == CONVERSATION_ID
    assert result["file_type"] == "pdf"
    assert result["chunk_count"] > 0

    # ---------------------------------------------------------
    # VERIFY LOCAL FILE
    # ---------------------------------------------------------

    downloaded_file = Path(
        result["file_path"]
    )

    print()
    print("-" * 50)
    print("DOWNLOADED FILE")
    print("-" * 50)

    print()
    print(f"File: {downloaded_file}")
    print(f"Exists: {downloaded_file.exists()}")

    assert downloaded_file.exists()
    assert downloaded_file.suffix.lower() == ".pdf"

    # ---------------------------------------------------------
    # VERIFY CHROMA
    # ---------------------------------------------------------

    chunks = get_test_chunks()

    print()
    print("-" * 50)
    print("CHROMA VERIFICATION")
    print("-" * 50)

    print()
    print(f"Stored Classroom chunks: {len(chunks)}")

    assert len(chunks) == result["chunk_count"]

    for chunk in chunks[:3]:
        print()
        print(
            f"ID: {chunk['id']}"
        )
        print(
            f"Metadata: {chunk['metadata']}"
        )
        print(
            f"Preview: "
            f"{chunk['text'][:200].replace(chr(10), ' ')}"
        )

    # ---------------------------------------------------------
    # VERIFY IMPORTANT METADATA
    # ---------------------------------------------------------

    for chunk in chunks:
        metadata = chunk["metadata"]

        assert (
            metadata.get("source_type")
            == "google_classroom"
        )

        assert (
            metadata.get("teacher_id")
            == TEACHER_ID
        )

        assert (
            metadata.get("school_id")
            == SCHOOL_ID
        )

        assert (
            metadata.get("conversation_id")
            == CONVERSATION_ID
        )

        assert (
            metadata.get("course_id")
            == COURSE_ID
        )

        assert (
            metadata.get("material_id")
            == MATERIAL_ID
        )

        assert metadata.get(
            "drive_file_id"
        )

        assert metadata.get(
            "material_title"
        )

        assert metadata.get(
            "file_name"
        )

    print()
    print("Classroom metadata verification passed.")

    # ---------------------------------------------------------
    # RAG RETRIEVAL TEST
    # ---------------------------------------------------------

    print()
    print("-" * 50)
    print("CLASSROOM RAG RETRIEVAL TEST")
    print("-" * 50)

    query = (
        "Explain Booth's algorithm "
        "and its step-by-step process."
    )

    print()
    print(f"Query: {query}")

    results = retrieve_documents(
        query,
        top_k=5,
        similarity_threshold=0.20,
        teacher_id=TEACHER_ID,
        school_id=SCHOOL_ID,
        conversation_id=CONVERSATION_ID,
        source_type="google_classroom",
    )

    print()
    print(
        f"Retrieved Classroom chunks: {len(results)}"
    )

    assert results, (
        "Classroom RAG returned no results."
    )

    for index, item in enumerate(
        results,
        start=1,
    ):
        metadata = item["metadata"]

        print()
        print(
            f"{index}. "
            f"similarity={item['similarity']:.4f}"
        )

        print(
            f"   teacher="
            f"{metadata.get('teacher_id')}"
        )

        print(
            f"   school="
            f"{metadata.get('school_id')}"
        )

        print(
            f"   source="
            f"{metadata.get('source_type')}"
        )

        print(
            f"   file="
            f"{metadata.get('file_name')}"
        )

        print(
            f"   material="
            f"{metadata.get('material_title')}"
        )

        print(
            f"   preview="
            f"{item['text'][:250].replace(chr(10), ' ')}"
        )

        assert (
            metadata.get("source_type")
            == "google_classroom"
        )

        assert (
            metadata.get("teacher_id")
            == TEACHER_ID
        )

        assert (
            metadata.get("school_id")
            == SCHOOL_ID
        )

        assert (
            metadata.get("conversation_id")
            == CONVERSATION_ID
        )

        assert (
            metadata.get("course_id")
            == COURSE_ID
        )

        assert (
            metadata.get("material_id")
            == MATERIAL_ID
        )

    print()
    print("Classroom RAG retrieval passed.")

    # ---------------------------------------------------------
    # DUPLICATE / IDEMPOTENCY TEST
    # ---------------------------------------------------------

    print()
    print("-" * 50)
    print("RE-INGESTION / DUPLICATE TEST")
    print("-" * 50)

    before_chunks = get_test_chunks()

    print()
    print(
        f"Chunks before re-ingestion: "
        f"{len(before_chunks)}"
    )

    second_result = service.ingest_material(
        course_id=COURSE_ID,
        material_id=MATERIAL_ID,
        teacher_id=TEACHER_ID,
        school_id=SCHOOL_ID,
        conversation_id=CONVERSATION_ID,
    )

    after_chunks = get_test_chunks()

    print(
        f"Chunks after re-ingestion: "
        f"{len(after_chunks)}"
    )

    assert (
        second_result["chunk_count"]
        == result["chunk_count"]
    )

    assert (
        len(after_chunks)
        == len(before_chunks)
    )

    print()
    print("Duplicate / idempotency test passed.")

    # ---------------------------------------------------------
    # FINAL
    # ---------------------------------------------------------

    print()
    print("=" * 50)
    print("GOOGLE CLASSROOM → RAG TEST PASSED")
    print("=" * 50)
    print()


if __name__ == "__main__":
    main()