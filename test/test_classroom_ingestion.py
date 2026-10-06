from __future__ import annotations

from pathlib import Path
import sys


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# IMPORTS
# ============================================================

from backend.services.classroom_ingestion import (
    ClassroomIngestionError,
    ClassroomIngestionService,
)

from backend.rag.vectorstore import (
    get_source_id_chunks,
)


# ============================================================
# TEST CONFIGURATION
# ============================================================

COURSE_ID = "871538502094"

MATERIAL_ID = "884229212233"

TEACHER_ID = "teacher-classroom-test"

SCHOOL_ID = "TCO_CLASSROOM_TEST"

CONVERSATION_ID = "conversation-classroom-rag-test"


# IMPORTANT:
# The Classroom material contains multiple attachments.
# We explicitly select the PDF required by this test.
ATTACHMENT_TITLE = (
    "Booth Algorithm Step-by-Step Examples.pdf"
)


# Expected Drive file ID for the above attachment.
EXPECTED_DRIVE_FILE_ID = (
    "1qBga7gdr-8dw1l2ozN1D3ndhirud7t51"
)


# Expected file type.
EXPECTED_FILE_TYPE = "pdf"


# ============================================================
# HELPERS
# ============================================================

def print_section(title: str) -> None:
    print()
    print("-" * 60)
    print(title)
    print("-" * 60)


def assert_result_field(
    result: dict,
    field: str,
    expected,
) -> None:
    actual = result.get(field)

    assert actual == expected, (
        f"Field '{field}' mismatch.\n"
        f"Expected: {expected!r}\n"
        f"Actual:   {actual!r}"
    )


# ============================================================
# MAIN TEST
# ============================================================

def main() -> None:

    print("=" * 60)
    print("TCO GOOGLE CLASSROOM → RAG TEST")
    print("=" * 60)

    print()
    print(f"Course ID:       {COURSE_ID}")
    print(f"Material ID:     {MATERIAL_ID}")
    print(f"Teacher ID:      {TEACHER_ID}")
    print(f"School ID:       {SCHOOL_ID}")
    print(f"Conversation ID:  {CONVERSATION_ID}")
    print(f"Attachment:      {ATTACHMENT_TITLE}")
    print(
        f"Expected Drive ID: {EXPECTED_DRIVE_FILE_ID}"
    )

    # --------------------------------------------------------
    # CREATE SERVICE
    # --------------------------------------------------------

    service = ClassroomIngestionService()

    # --------------------------------------------------------
    # FIRST INGESTION
    # --------------------------------------------------------

    print_section(
        "FIRST CLASSROOM INGESTION"
    )

    try:
        result = service.ingest_material(
            course_id=COURSE_ID,
            material_id=MATERIAL_ID,
            teacher_id=TEACHER_ID,
            school_id=SCHOOL_ID,
            conversation_id=CONVERSATION_ID,
            attachment_title=ATTACHMENT_TITLE,
        )

    except ClassroomIngestionError as exc:

        raise AssertionError(
            "Classroom ingestion failed:\n"
            f"{exc}"
        ) from exc

    print()
    print("Ingestion result:")
    print(result)

    # --------------------------------------------------------
    # BASIC RESULT VALIDATION
    # --------------------------------------------------------

    assert isinstance(result, dict), (
        "Ingestion result must be a dictionary."
    )

    assert_result_field(
        result,
        "success",
        True,
    )

    assert_result_field(
        result,
        "source_type",
        "google_classroom",
    )

    assert_result_field(
        result,
        "course_id",
        COURSE_ID,
    )

    assert_result_field(
        result,
        "material_id",
        MATERIAL_ID,
    )

    assert_result_field(
        result,
        "teacher_id",
        TEACHER_ID,
    )

    assert_result_field(
        result,
        "school_id",
        SCHOOL_ID,
    )

    assert_result_field(
        result,
        "conversation_id",
        CONVERSATION_ID,
    )

    # --------------------------------------------------------
    # ATTACHMENT VALIDATION
    # --------------------------------------------------------

    print_section(
        "ATTACHMENT VALIDATION"
    )

    actual_attachment_title = str(
        result.get(
            "attachment_title",
            "",
        )
    ).strip()

    actual_drive_file_id = str(
        result.get(
            "drive_file_id",
            "",
        )
    ).strip()

    actual_file_name = str(
        result.get(
            "file_name",
            "",
        )
    ).strip()

    actual_file_type = str(
        result.get(
            "file_type",
            "",
        )
    ).strip().lower()

    print(
        f"Selected attachment: "
        f"{actual_attachment_title}"
    )

    print(
        f"Drive file ID: "
        f"{actual_drive_file_id}"
    )

    print(
        f"Downloaded file: "
        f"{actual_file_name}"
    )

    print(
        f"File type: "
        f"{actual_file_type}"
    )

    assert (
        actual_attachment_title
        == ATTACHMENT_TITLE
    ), (
        "Wrong Classroom attachment selected.\n"
        f"Expected: {ATTACHMENT_TITLE}\n"
        f"Actual:   {actual_attachment_title}"
    )

    assert (
        actual_drive_file_id
        == EXPECTED_DRIVE_FILE_ID
    ), (
        "Wrong Drive file selected.\n"
        f"Expected: {EXPECTED_DRIVE_FILE_ID}\n"
        f"Actual:   {actual_drive_file_id}"
    )

    assert (
        actual_file_type
        == EXPECTED_FILE_TYPE
    ), (
        "Wrong downloaded file type.\n"
        f"Expected: {EXPECTED_FILE_TYPE}\n"
        f"Actual:   {actual_file_type}"
    )

    assert actual_file_name, (
        "Downloaded file name is empty."
    )

    assert actual_file_name.lower().endswith(
        ".pdf"
    ), (
        "Selected file is not a PDF.\n"
        f"File: {actual_file_name}"
    )

    print()
    print(
        "Attachment selection test passed."
    )

    # --------------------------------------------------------
    # FILE PATH VALIDATION
    # --------------------------------------------------------

    print_section(
        "DOWNLOADED FILE VALIDATION"
    )

    file_path_value = str(
        result.get(
            "file_path",
            "",
        )
    ).strip()

    assert file_path_value, (
        "file_path is missing from ingestion result."
    )

    file_path = Path(file_path_value)

    print(
        f"File path: {file_path}"
    )

    assert file_path.exists(), (
        "Downloaded Classroom file does not exist:\n"
        f"{file_path}"
    )

    assert file_path.is_file(), (
        "Downloaded Classroom path is not a file:\n"
        f"{file_path}"
    )

    file_size = file_path.stat().st_size

    print(
        f"File size: {file_size:,} bytes"
    )

    assert file_size > 0, (
        "Downloaded Classroom file is empty."
    )

    print(
        "Downloaded file test passed."
    )

    # --------------------------------------------------------
    # DOCUMENT COUNT
    # --------------------------------------------------------

    print_section(
        "DOCUMENT / CHUNK VALIDATION"
    )

    document_count = result.get(
        "document_count"
    )

    chunk_count = result.get(
        "chunk_count"
    )

    source_id = str(
        result.get(
            "source_id",
            "",
        )
    ).strip()

    print(
        f"Document count: {document_count}"
    )

    print(
        f"Chunk count:    {chunk_count}"
    )

    print(
        f"Source ID:      {source_id}"
    )

    assert isinstance(
        document_count,
        int,
    ), (
        "document_count must be an integer."
    )

    assert document_count > 0, (
        "No documents were produced."
    )

    assert isinstance(
        chunk_count,
        int,
    ), (
        "chunk_count must be an integer."
    )

    assert chunk_count > 0, (
        "No chunks were produced."
    )

    assert source_id, (
        "source_id is missing."
    )

    print(
        "Document/chunk validation passed."
    )

    # --------------------------------------------------------
    # SOURCE ID CHUNK VALIDATION
    # --------------------------------------------------------

    print_section(
        "VECTORSTORE SOURCE-ID VALIDATION"
    )

    source_chunks = get_source_id_chunks(
        source_id
    )

    print(
        f"Stored source-id chunks: "
        f"{len(source_chunks)}"
    )

    assert len(source_chunks) == chunk_count, (
        "Vectorstore chunk count mismatch.\n"
        f"Expected: {chunk_count}\n"
        f"Stored:   {len(source_chunks)}"
    )

    print(
        "Source-ID vectorstore validation passed."
    )

    # --------------------------------------------------------
    # METADATA VALIDATION
    # --------------------------------------------------------

    print_section(
        "METADATA ISOLATION VALIDATION"
    )

    first_chunk = source_chunks[0]

    if isinstance(first_chunk, dict):
        metadata = first_chunk.get(
            "metadata",
            {},
        )

        if not metadata:
            # Some vectorstore implementations may
            # return flattened metadata.
            metadata = first_chunk
    else:
        metadata = {}

    assert isinstance(
        metadata,
        dict,
    ), (
        "Stored chunk metadata must be a dictionary."
    )

    print()
    print("First chunk metadata:")
    print(metadata)

    expected_metadata = {
        "teacher_id": TEACHER_ID,
        "school_id": SCHOOL_ID,
        "conversation_id": CONVERSATION_ID,
        "course_id": COURSE_ID,
        "material_id": MATERIAL_ID,
        "source_type": "google_classroom",
    }

    for key, expected_value in (
        expected_metadata.items()
    ):

        if key not in metadata:
            print(
                f"WARNING: metadata key '{key}' "
                "not directly available in returned "
                "chunk structure."
            )
            continue

        actual_value = metadata.get(key)

        assert actual_value == expected_value, (
            f"Metadata mismatch for '{key}'.\n"
            f"Expected: {expected_value!r}\n"
            f"Actual:   {actual_value!r}"
        )

    if "source_id" in metadata:

        assert (
            metadata["source_id"]
            == source_id
        ), (
            "Metadata source_id does not match "
            "ingestion source_id."
        )

    print(
        "Metadata validation passed."
    )

    # --------------------------------------------------------
    # RE-INGESTION / DUPLICATE TEST
    # --------------------------------------------------------

    print_section(
        "RE-INGESTION / DUPLICATE TEST"
    )

    before_reingestion = len(
        get_source_id_chunks(
            source_id
        )
    )

    print(
        f"Stored chunks before re-ingestion: "
        f"{before_reingestion}"
    )

    try:
        second_result = service.ingest_material(
            course_id=COURSE_ID,
            material_id=MATERIAL_ID,
            teacher_id=TEACHER_ID,
            school_id=SCHOOL_ID,
            conversation_id=CONVERSATION_ID,
            attachment_title=ATTACHMENT_TITLE,
        )

    except ClassroomIngestionError as exc:

        raise AssertionError(
            "Classroom re-ingestion failed:\n"
            f"{exc}"
        ) from exc

    second_chunk_count = second_result.get(
        "chunk_count"
    )

    print(
        f"First ingestion chunks:  "
        f"{chunk_count}"
    )

    print(
        f"Second ingestion chunks: "
        f"{second_chunk_count}"
    )

    after_reingestion = len(
        get_source_id_chunks(
            source_id
        )
    )

    print(
        f"Stored chunks after re-ingestion: "
        f"{after_reingestion}"
    )

    assert (
        second_result.get("source_id")
        == source_id
    ), (
        "Re-ingestion generated a different source_id."
    )

    assert (
        second_chunk_count
        == chunk_count
    ), (
        "Chunk count changed during re-ingestion.\n"
        f"First:  {chunk_count}\n"
        f"Second: {second_chunk_count}"
    )

    assert (
        after_reingestion
        == before_reingestion
    ), (
        "Duplicate chunks were created during "
        "re-ingestion.\n"
        f"Before: {before_reingestion}\n"
        f"After:  {after_reingestion}"
    )

    print(
        "Duplicate/re-ingestion test passed."
    )

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print(
        "CLASSROOM → RAG TEST PASSED"
    )
    print("=" * 60)

    print()
    print("Summary:")
    print(
        f"  Attachment : {actual_attachment_title}"
    )
    print(
        f"  Drive ID   : {actual_drive_file_id}"
    )
    print(
        f"  File       : {actual_file_name}"
    )
    print(
        f"  File type  : {actual_file_type}"
    )
    print(
        f"  Documents  : {document_count}"
    )
    print(
        f"  Chunks     : {chunk_count}"
    )
    print(
        f"  Source ID  : {source_id}"
    )
    print(
        f"  Re-ingest  : {after_reingestion} stored chunks"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print()
        print("=" * 60)
        print(
            "CLASSROOM → RAG TEST FAILED"
        )
        print("=" * 60)
        print()
        print(exc)
        raise