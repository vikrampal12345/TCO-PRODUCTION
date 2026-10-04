from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import numpy as np
import pymupdf
from PIL import Image
from pptx import Presentation


class DocumentLoaderError(Exception):
    """Raised when a document cannot be loaded."""


# =============================================================
# PDF
# =============================================================

def load_pdf(
    file_path: str,
) -> list[dict[str, Any]]:
    """
    Load a PDF page-by-page.
    """
    path = Path(file_path)

    if not path.exists():
        raise DocumentLoaderError(
            f"PDF file not found: {path}"
        )

    if path.suffix.lower() != ".pdf":
        raise DocumentLoaderError(
            f"Expected a PDF file, got: {path.suffix}"
        )

    documents: list[dict[str, Any]] = []

    try:
        pdf = pymupdf.open(
            str(path)
        )
    except Exception as exc:
        raise DocumentLoaderError(
            f"Could not open PDF '{path.name}': {exc}"
        ) from exc

    try:
        for page_number, page in enumerate(
            pdf,
            start=1,
        ):
            text = page.get_text(
                "text"
            ).strip()

            if not text:
                continue

            documents.append(
                {
                    "text": text,
                    "metadata": {
                        "source": str(path),
                        "file_name": path.name,
                        "file_type": "pdf",
                        "page": page_number,
                    },
                }
            )
    finally:
        pdf.close()

    return documents


# =============================================================
# PPTX OCR
# =============================================================

_ocr_reader = None


def _get_ocr_reader():
    """
    Lazily create the EasyOCR reader.

    OCR model initialization is intentionally delayed until
    an image actually needs OCR.
    """
    global _ocr_reader

    if _ocr_reader is not None:
        return _ocr_reader

    try:
        import easyocr
    except ImportError as exc:
        raise DocumentLoaderError(
            "EasyOCR is required for image-based PPTX files.\n"
            "Install it with:\n"
            "python -m pip install easyocr pillow numpy"
        ) from exc

    try:
        _ocr_reader = easyocr.Reader(
            ["en"],
            gpu=False,
            verbose=False,
        )
    except Exception as exc:
        raise DocumentLoaderError(
            f"Could not initialize EasyOCR: {exc}"
        ) from exc

    return _ocr_reader


def _ocr_image_bytes(
    image_bytes: bytes,
) -> str:
    """
    Run OCR on embedded image bytes.
    """
    if not image_bytes:
        return ""

    try:
        image = Image.open(
            io.BytesIO(image_bytes)
        )

        image = image.convert(
            "RGB"
        )

        image_array = np.array(
            image
        )

    except Exception as exc:
        raise DocumentLoaderError(
            f"Could not decode PPTX image for OCR: {exc}"
        ) from exc

    reader = _get_ocr_reader()

    try:
        results = reader.readtext(
            image_array,
            detail=0,
            paragraph=False,
        )
    except Exception as exc:
        raise DocumentLoaderError(
            f"OCR failed on PPTX image: {exc}"
        ) from exc

    cleaned_lines: list[str] = []

    for result in results:
        text = str(
            result
        ).strip()

        if text:
            cleaned_lines.append(
                text
            )

    return "\n".join(
        cleaned_lines
    ).strip()


def _extract_picture_ocr(
    shape: Any,
) -> str:
    """
    Extract and OCR a PowerPoint picture shape.
    """
    try:
        image = shape.image
        image_bytes = image.blob
    except Exception:
        return ""

    if not image_bytes:
        return ""

    return _ocr_image_bytes(
        image_bytes
    )


# =============================================================
# PPTX SHAPE EXTRACTION
# =============================================================

def _extract_shape_text(
    shape: Any,
) -> str:
    """
    Extract normal PowerPoint text recursively.

    Handles:
    - text boxes
    - titles
    - subtitles
    - tables
    - grouped shapes
    """
    parts: list[str] = []

    # ---------------------------------------------------------
    # Normal text
    # ---------------------------------------------------------

    if hasattr(
        shape,
        "has_text_frame",
    ):
        try:
            if shape.has_text_frame:
                text = shape.text.strip()

                if text:
                    parts.append(
                        text
                    )
        except Exception:
            pass

    # ---------------------------------------------------------
    # Tables
    # ---------------------------------------------------------

    if getattr(
        shape,
        "has_table",
        False,
    ):
        try:
            table = shape.table

            for row in table.rows:
                row_values: list[str] = []

                for cell in row.cells:
                    cell_text = (
                        cell.text.strip()
                    )

                    if cell_text:
                        row_values.append(
                            cell_text
                        )

                if row_values:
                    parts.append(
                        " | ".join(
                            row_values
                        )
                    )

        except Exception:
            pass

    # ---------------------------------------------------------
    # Grouped shapes
    # ---------------------------------------------------------

    if hasattr(
        shape,
        "shapes",
    ):
        try:
            for child_shape in shape.shapes:
                child_text = (
                    _extract_shape_text(
                        child_shape
                    )
                )

                if child_text:
                    parts.append(
                        child_text
                    )

        except Exception:
            pass

    return "\n".join(
        parts
    ).strip()


def _extract_slide_text(
    slide: Any,
) -> tuple[str, bool, int]:
    """
    Extract both normal text and image OCR from a slide.

    Returns:
        text
        ocr_used
        image_count
    """
    parts: list[str] = []

    ocr_used = False
    image_count = 0

    for shape in slide.shapes:

        # -----------------------------------------------------
        # Normal text/table/group extraction
        # -----------------------------------------------------

        shape_text = _extract_shape_text(
            shape
        )

        if shape_text:
            parts.append(
                shape_text
            )

        # -----------------------------------------------------
        # Picture OCR
        # -----------------------------------------------------

        shape_type_name = str(
            getattr(
                getattr(
                    shape,
                    "shape_type",
                    None,
                ),
                "name",
                "",
            )
        )

        is_picture = (
            shape_type_name
            == "PICTURE"
        )

        if is_picture:
            image_count += 1

            try:
                ocr_text = (
                    _extract_picture_ocr(
                        shape
                    )
                )
            except DocumentLoaderError:
                raise

            if ocr_text:
                parts.append(
                    "[OCR]\n"
                    + ocr_text
                )

                ocr_used = True

    # Remove repeated blank lines.
    text = "\n".join(
        part
        for part in parts
        if part.strip()
    ).strip()

    return (
        text,
        ocr_used,
        image_count,
    )


# =============================================================
# PPTX
# =============================================================

def load_pptx(
    file_path: str,
) -> list[dict[str, Any]]:
    """
    Load a PPTX slide-by-slide.

    Supports:
    - normal PowerPoint text
    - tables
    - grouped shapes
    - image-only slides through OCR
    """
    path = Path(file_path)

    if not path.exists():
        raise DocumentLoaderError(
            f"PPTX file not found: {path}"
        )

    if path.suffix.lower() != ".pptx":
        raise DocumentLoaderError(
            f"Expected a PPTX file, got: {path.suffix}"
        )

    try:
        presentation = Presentation(
            str(path)
        )
    except Exception as exc:
        raise DocumentLoaderError(
            f"Could not open PPTX '{path.name}': {exc}"
        ) from exc

    documents: list[
        dict[str, Any]
    ] = []

    for slide_number, slide in enumerate(
        presentation.slides,
        start=1,
    ):
        text, ocr_used, image_count = (
            _extract_slide_text(
                slide
            )
        )

        if not text:
            continue

        documents.append(
            {
                "text": text,
                "metadata": {
                    "source": str(path),
                    "file_name": path.name,
                    "file_type": "pptx",
                    "slide": slide_number,
                    "ocr_used": ocr_used,
                    "image_count": image_count,
                },
            }
        )

    return documents


# =============================================================
# TXT / MD
# =============================================================

def load_text_file(
    file_path: str,
) -> list[dict[str, Any]]:
    """
    Load TXT or Markdown as one document.
    """
    path = Path(file_path)

    if not path.exists():
        raise DocumentLoaderError(
            f"Text file not found: {path}"
        )

    if path.suffix.lower() not in {
        ".txt",
        ".md",
    }:
        raise DocumentLoaderError(
            f"Unsupported text file type: "
            f"{path.suffix}"
        )

    try:
        text = path.read_text(
            encoding="utf-8",
            errors="ignore",
        ).strip()
    except Exception as exc:
        raise DocumentLoaderError(
            f"Could not read '{path.name}': {exc}"
        ) from exc

    if not text:
        return []

    return [
        {
            "text": text,
            "metadata": {
                "source": str(path),
                "file_name": path.name,
                "file_type": (
                    path.suffix
                    .lower()
                    .lstrip(".")
                ),
            },
        }
    ]


# =============================================================
# AUTO LOADER
# =============================================================

def load_file(
    file_path: str,
) -> list[dict[str, Any]]:
    """
    Automatically select the appropriate loader.

    Supported:
    - PDF
    - PPTX
    - TXT
    - MD
    """
    path = Path(file_path)

    if not path.exists():
        raise DocumentLoaderError(
            f"File not found: {path}"
        )

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return load_pdf(
            str(path)
        )

    if suffix == ".pptx":
        return load_pptx(
            str(path)
        )

    if suffix in {
        ".txt",
        ".md",
    }:
        return load_text_file(
            str(path)
        )

    raise DocumentLoaderError(
        f"Unsupported file type '{suffix}'. "
        "Supported types: "
        ".pdf, .pptx, .txt, .md"
    )