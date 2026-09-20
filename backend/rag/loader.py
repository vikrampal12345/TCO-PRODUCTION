import pymupdf


def load_pdf(file_path: str) -> list[dict]:
    """
    Load text from a PDF.

    Each PDF page becomes one document with metadata.
    """

    documents = []

    pdf = pymupdf.open(file_path)

    try:
        for page_number, page in enumerate(pdf, start=1):

            text = page.get_text("text").strip()

            if not text:
                continue

            documents.append(
                {
                    "text": text,
                    "metadata": {
                        "source": file_path,
                        "page": page_number,
                    },
                }
            )

    finally:
        pdf.close()

    return documents