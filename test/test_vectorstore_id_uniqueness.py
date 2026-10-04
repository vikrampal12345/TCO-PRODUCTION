from __future__ import annotations

from backend.rag.vectorstore import (
    _build_chunk_id,
)


def main() -> None:
    print()
    print("=" * 50)
    print("TCO VECTOR STORE ID UNIQUENESS TEST")
    print("=" * 50)

    source_id = (
        "classroom_test_source"
    )

    # ---------------------------------------------------------
    # SIMULATE PPTX SLIDES
    # ---------------------------------------------------------

    slide_1_metadata = {
        "source": "test.pptx",
        "file_name": "test.pptx",
        "file_type": "pptx",
        "slide": 1,
    }

    slide_2_metadata = {
        "source": "test.pptx",
        "file_name": "test.pptx",
        "file_type": "pptx",
        "slide": 2,
    }

    id_1 = _build_chunk_id(
        source_id=source_id,
        metadata=slide_1_metadata,
        document_index=0,
        chunk_in_document=0,
        text="Booth Algorithm slide one",
    )

    id_2 = _build_chunk_id(
        source_id=source_id,
        metadata=slide_2_metadata,
        document_index=1,
        chunk_in_document=0,
        text="Booth Algorithm slide two",
    )

    print()
    print("Slide 1 ID:")
    print(id_1)

    print()
    print("Slide 2 ID:")
    print(id_2)

    assert id_1 != id_2

    print()
    print(
        "Slide IDs are unique."
    )

    # ---------------------------------------------------------
    # SAME SLIDE / SAME CONTENT
    # ---------------------------------------------------------

    id_1_repeat = _build_chunk_id(
        source_id=source_id,
        metadata=slide_1_metadata,
        document_index=0,
        chunk_in_document=0,
        text="Booth Algorithm slide one",
    )

    print()
    print("Repeated Slide 1 ID:")
    print(id_1_repeat)

    assert id_1 == id_1_repeat

    print()
    print(
        "Deterministic ID test passed."
    )

    # ---------------------------------------------------------
    # SAME SOURCE / DIFFERENT CONTENT
    # ---------------------------------------------------------

    id_1_changed = _build_chunk_id(
        source_id=source_id,
        metadata=slide_1_metadata,
        document_index=0,
        chunk_in_document=0,
        text="Different slide content",
    )

    assert id_1 != id_1_changed

    print()
    print(
        "Content collision protection passed."
    )

    # ---------------------------------------------------------
    # FINAL
    # ---------------------------------------------------------

    print()
    print("=" * 50)
    print("VECTOR STORE ID TEST PASSED")
    print("=" * 50)
    print()


if __name__ == "__main__":
    main()