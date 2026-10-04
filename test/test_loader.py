from pathlib import Path

from backend.rag.loader import load_file


BASE_DIR = Path(__file__).resolve().parent.parent

PDF_PATH = (
    BASE_DIR
    / "data"
    / "documents"
    / "sql_notes.pdf"
)


def main() -> None:
    print(
        "\n========================================"
    )
    print(
        "TCO DOCUMENT LOADER TEST"
    )
    print(
        "========================================"
    )

    print(
        "\nLoading:"
    )
    print(
        PDF_PATH
    )

    documents = load_file(
        str(PDF_PATH)
    )

    print(
        "\nDocuments loaded:",
        len(documents),
    )

    for document in documents:
        print(
            "\n----------------------------------------"
        )

        print(
            "Metadata:"
        )

        print(
            document["metadata"]
        )

        print(
            "\nText preview:"
        )

        print(
            document["text"][:500]
        )

    if not documents:
        raise RuntimeError(
            "Loader returned zero documents."
        )

    print(
        "\n========================================"
    )

    print(
        "LOADER TEST PASSED"
    )

    print(
        "========================================"
    )


if __name__ == "__main__":
    main()