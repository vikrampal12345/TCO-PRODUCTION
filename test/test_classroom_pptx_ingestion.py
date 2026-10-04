from __future__ import annotations

from pathlib import Path

from backend.rag.retriever import retrieve_documents
from backend.rag.vectorstore import collection
from backend.services.classroom_ingestion import (
    ClassroomIngestionError,
    ClassroomIngestionService,
)


COURSE_ID = "871538502094"

MATERIAL_ID = "884229212233"

DRIVE_FILE_ID = (
    "1XaCuFIF2vddUX1KoZfHWK1KtKjUz1vVj"
)

ATTACHMENT_TITLE = (
    "Array Multiplier and Booth.pptx"
)

TEACHER_ID = (
    "teacher-classroom-pptx-test"
)

SCHOOL_ID = (
    "TCO_CLASSROOM_PPTX_TEST"
)

CONVERSATION_ID = (
    "conversation-classroom-pptx-test"
)


# =============================================================
# CLEANUP
# =============================================================

def cleanup_test_scope() -> int:
    """
    Remove only chunks created by this specific test.
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

    for index, metadata in enumerate(
        metadatas
    ):
        if index >= len(ids):
            break

        metadata = metadata or {}

        if (
            metadata.get(
                "source_type"
            )
            == "google_classroom"

            and metadata.get(
                "teacher_id"
            )
            == TEACHER_ID

            and metadata.get(
                "school_id"
            )
            == SCHOOL_ID

            and metadata.get(
                "conversation_id"
            )
            == CONVERSATION_ID
        ):
            ids_to_delete.append(
                ids[index]
            )

    if ids_to_delete:
        collection.delete(
            ids=ids_to_delete
        )

    return len(
        ids_to_delete
    )


# =============================================================
# GET TEST CHUNKS
# =============================================================

def get_test_chunks() -> list[dict]:
    """
    Return all Chroma chunks belonging to this test.
    """

    stored = collection.get(
        include=[
            "metadatas",
            "documents",
        ]
    )

    ids = stored.get(
        "ids",
        [],
    )

    metadatas = stored.get(
        "metadatas",
        [],
    )

    documents = stored.get(
        "documents",
        [],
    )

    chunks: list[dict] = []

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

        metadata = (
            metadata or {}
        )

        if (
            metadata.get(
                "source_type"
            )
            == "google_classroom"

            and metadata.get(
                "teacher_id"
            )
            == TEACHER_ID

            and metadata.get(
                "school_id"
            )
            == SCHOOL_ID

            and metadata.get(
                "conversation_id"
            )
            == CONVERSATION_ID
        ):
            chunks.append(
                {
                    "id": document_id,
                    "metadata": metadata,
                    "text": document,
                }
            )

    return chunks


# =============================================================
# MAIN TEST
# =============================================================

def main() -> None:

    print()
    print("=" * 50)
    print(
        "TCO GOOGLE CLASSROOM PPTX → RAG TEST"
    )
    print("=" * 50)

    print()
    print(
        f"Course ID:       {COURSE_ID}"
    )

    print(
        f"Material ID:     {MATERIAL_ID}"
    )

    print(
        f"Drive File ID:   {DRIVE_FILE_ID}"
    )

    print(
        f"Attachment:      {ATTACHMENT_TITLE}"
    )

    # =========================================================
    # CLEAN OLD TEST DATA
    # =========================================================

    removed = cleanup_test_scope()

    print()
    print(
        f"Old PPTX test chunks removed: {removed}"
    )

    service = (
        ClassroomIngestionService()
    )

    # =========================================================
    # FIRST INGESTION
    # =========================================================

    print()
    print("-" * 50)
    print(
        "CLASSROOM PPTX INGESTION"
    )
    print("-" * 50)

    try:
        first_ingestion_result = (
            service.ingest_material(
                course_id=COURSE_ID,
                material_id=MATERIAL_ID,
                teacher_id=TEACHER_ID,
                school_id=SCHOOL_ID,
                conversation_id=CONVERSATION_ID,
                drive_file_id=DRIVE_FILE_ID,
                attachment_title=ATTACHMENT_TITLE,
            )
        )

    except ClassroomIngestionError as exc:
        raise AssertionError(
            f"PPTX ingestion failed: {exc}"
        ) from exc

    print()
    print(
        "Ingestion result:"
    )

    print(
        first_ingestion_result
    )

    # ---------------------------------------------------------
    # INGESTION ASSERTIONS
    # ---------------------------------------------------------

    assert (
        first_ingestion_result[
            "success"
        ]
        is True
    )

    assert (
        first_ingestion_result[
            "source_type"
        ]
        == "google_classroom"
    )

    assert (
        first_ingestion_result[
            "teacher_id"
        ]
        == TEACHER_ID
    )

    assert (
        first_ingestion_result[
            "school_id"
        ]
        == SCHOOL_ID
    )

    assert (
        first_ingestion_result[
            "conversation_id"
        ]
        == CONVERSATION_ID
    )

    assert (
        first_ingestion_result[
            "course_id"
        ]
        == COURSE_ID
    )

    assert (
        first_ingestion_result[
            "material_id"
        ]
        == MATERIAL_ID
    )

    assert (
        first_ingestion_result[
            "drive_file_id"
        ]
        == DRIVE_FILE_ID
    )

    assert (
        first_ingestion_result[
            "drive_file_name"
        ]
        == ATTACHMENT_TITLE
    )

    assert (
        first_ingestion_result[
            "file_type"
        ]
        == "pptx"
    )

    assert (
        first_ingestion_result[
            "document_count"
        ]
        > 0
    )

    assert (
        first_ingestion_result[
            "chunk_count"
        ]
        > 0
    )

    # =========================================================
    # DOWNLOADED FILE
    # =========================================================

    downloaded_file = Path(
        first_ingestion_result[
            "file_path"
        ]
    )

    print()
    print("-" * 50)
    print(
        "DOWNLOADED PPTX"
    )
    print("-" * 50)

    print()
    print(
        f"File: {downloaded_file}"
    )

    print(
        f"Exists: {downloaded_file.exists()}"
    )

    if downloaded_file.exists():
        print(
            f"Size: "
            f"{downloaded_file.stat().st_size}"
        )

    assert downloaded_file.exists()

    assert (
        downloaded_file.suffix.lower()
        == ".pptx"
    )

    assert (
        downloaded_file.stat().st_size
        > 0
    )

    # =========================================================
    # CHROMA VERIFICATION
    # =========================================================

    test_chunks = get_test_chunks()

    print()
    print("-" * 50)
    print(
        "CHROMA VERIFICATION"
    )
    print("-" * 50)

    print()
    print(
        f"Stored PPTX chunks: "
        f"{len(test_chunks)}"
    )

    assert (
        len(test_chunks)
        == first_ingestion_result[
            "chunk_count"
        ]
    )

    # ---------------------------------------------------------
    # DISPLAY FIRST FEW CHUNKS
    # ---------------------------------------------------------

    for chunk in test_chunks[:5]:

        print()
        print(
            f"ID: {chunk['id']}"
        )

        print(
            f"Metadata: "
            f"{chunk['metadata']}"
        )

        preview = (
            chunk["text"][:300]
            .replace(
                "\n",
                " ",
            )
        )

        print(
            f"Preview: {preview}"
        )

    # =========================================================
    # METADATA VERIFICATION
    # =========================================================

    for chunk in test_chunks:

        metadata = chunk[
            "metadata"
        ]

        assert (
            metadata.get(
                "source_type"
            )
            == "google_classroom"
        )

        assert (
            metadata.get(
                "teacher_id"
            )
            == TEACHER_ID
        )

        assert (
            metadata.get(
                "school_id"
            )
            == SCHOOL_ID
        )

        assert (
            metadata.get(
                "conversation_id"
            )
            == CONVERSATION_ID
        )

        assert (
            metadata.get(
                "course_id"
            )
            == COURSE_ID
        )

        assert (
            metadata.get(
                "material_id"
            )
            == MATERIAL_ID
        )

        assert (
            metadata.get(
                "drive_file_id"
            )
            == DRIVE_FILE_ID
        )

        assert (
            metadata.get(
                "file_type"
            )
            == "pptx"
        )

        assert (
            metadata.get(
                "slide"
            )
            is not None
        )

        assert (
            metadata.get(
                "ocr_used"
            )
            is True
        )

    print()
    print(
        "PPTX Classroom metadata verification passed."
    )

    # =========================================================
    # RAG RETRIEVAL
    # =========================================================

    print()
    print("-" * 50)
    print(
        "PPTX RAG RETRIEVAL TEST"
    )
    print("-" * 50)

    query = (
        "Explain Array Multiplier and "
        "Booth multiplication."
    )

    print()
    print(
        f"Query: {query}"
    )

    retrieval_results = retrieve_documents(
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
        f"Retrieved PPTX chunks: "
        f"{len(retrieval_results)}"
    )

    assert retrieval_results, (
        "No PPTX chunks were retrieved."
    )

    for index, retrieval_item in enumerate(
        retrieval_results,
        start=1,
    ):

        metadata = (
            retrieval_item[
                "metadata"
            ]
        )

        print()
        print(
            f"{index}. "
            f"similarity="
            f"{retrieval_item['similarity']:.4f}"
        )

        print(
            f"   file="
            f"{metadata.get('file_name')}"
        )

        print(
            f"   slide="
            f"{metadata.get('slide')}"
        )

        print(
            f"   source="
            f"{metadata.get('source_type')}"
        )

        preview = (
            retrieval_item[
                "text"
            ][:300]
            .replace(
                "\n",
                " ",
            )
        )

        print(
            f"   preview="
            f"{preview}"
        )

        # -----------------------------------------------------
        # SCOPE ASSERTIONS
        # -----------------------------------------------------

        assert (
            metadata.get(
                "teacher_id"
            )
            == TEACHER_ID
        )

        assert (
            metadata.get(
                "school_id"
            )
            == SCHOOL_ID
        )

        assert (
            metadata.get(
                "conversation_id"
            )
            == CONVERSATION_ID
        )

        assert (
            metadata.get(
                "source_type"
            )
            == "google_classroom"
        )

        assert (
            metadata.get(
                "file_type"
            )
            == "pptx"
        )

        assert (
            metadata.get(
                "drive_file_id"
            )
            == DRIVE_FILE_ID
        )

    print()
    print(
        "PPTX RAG retrieval passed."
    )

    # =========================================================
    # DUPLICATE / IDEMPOTENCY TEST
    # =========================================================

    print()
    print("-" * 50)
    print(
        "PPTX RE-INGESTION TEST"
    )
    print("-" * 50)

    chunks_before = (
        get_test_chunks()
    )

    print()
    print(
        f"Chunks before: "
        f"{len(chunks_before)}"
    )

    try:
        second_ingestion_result = (
            service.ingest_material(
                course_id=COURSE_ID,
                material_id=MATERIAL_ID,
                teacher_id=TEACHER_ID,
                school_id=SCHOOL_ID,
                conversation_id=CONVERSATION_ID,
                drive_file_id=DRIVE_FILE_ID,
                attachment_title=ATTACHMENT_TITLE,
            )
        )

    except ClassroomIngestionError as exc:
        raise AssertionError(
            f"Second PPTX ingestion failed: {exc}"
        ) from exc

    chunks_after = (
        get_test_chunks()
    )

    print()
    print(
        f"Chunks after:  "
        f"{len(chunks_after)}"
    )

    # ---------------------------------------------------------
    # SECOND INGESTION MUST SUCCEED
    # ---------------------------------------------------------

    assert (
        second_ingestion_result[
            "success"
        ]
        is True
    )

    # ---------------------------------------------------------
    # CHUNK COUNT MUST REMAIN THE SAME
    # ---------------------------------------------------------

    assert (
        second_ingestion_result[
            "chunk_count"
        ]
        == first_ingestion_result[
            "chunk_count"
        ]
    )

    # ---------------------------------------------------------
    # CHROMA COUNT MUST NOT INCREASE
    # ---------------------------------------------------------

    assert (
        len(chunks_after)
        == len(chunks_before)
    )

    # ---------------------------------------------------------
    # SOURCE ID MUST REMAIN DETERMINISTIC
    # ---------------------------------------------------------

    assert (
        second_ingestion_result[
            "source_id"
        ]
        == first_ingestion_result[
            "source_id"
        ]
    )

    print()
    print(
        "PPTX duplicate/idempotency test passed."
    )

    # =========================================================
    # FINAL
    # =========================================================

    print()
    print("=" * 50)
    print(
        "GOOGLE CLASSROOM PPTX → RAG TEST PASSED"
    )
    print("=" * 50)
    print()


if __name__ == "__main__":
    main()