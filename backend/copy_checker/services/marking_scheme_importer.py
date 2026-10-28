from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

from backend.copy_checker.schemas.marking_scheme import (
    MarkingScheme,
    QuestionMarkingScheme,
)


class MarkingSchemeImportError(ValueError):
    """The uploaded marking scheme is invalid or not locked."""


def load_marking_scheme(path: str | Path) -> MarkingScheme:
    """Parse the TCO locked-marking-scheme TXT/CSV format used by the demo.

    Supported question types in this import format are MCQ and short answer.
    Short-answer rows use Correct_Answer as evaluation guidance/reference text.
    """
    source = Path(path)
    if source.suffix.lower() != ".txt":
        raise MarkingSchemeImportError("Marking scheme must be a .txt file.")

    try:
        raw = source.read_text(encoding="utf-8-sig").strip()
    except OSError as exc:
        raise MarkingSchemeImportError(f"Cannot read marking scheme: {exc}") from exc
    if not raw:
        raise MarkingSchemeImportError("Marking scheme TXT file is empty.")

    lines = [line.strip() for line in raw.splitlines()
             if line.strip() and not line.strip().startswith("#")]
    assessment_id: str | None = None
    status: str | None = None
    mcq_marks: float | None = None
    short_answer_marks: float | None = None
    declared_total: float | None = None
    header_index: int | None = None

    def parse_float(value: str, label: str) -> float:
        try:
            number = float(value.strip())
        except (TypeError, ValueError) as exc:
            raise MarkingSchemeImportError(f"Invalid {label} value.") from exc
        if number < 0:
            raise MarkingSchemeImportError(f"{label} cannot be negative.")
        return number

    for index, line in enumerate(lines):
        upper = line.upper()
        if upper.startswith("ASSESSMENT_ID:"):
            assessment_id = line.split(":", 1)[1].strip()
        elif upper.startswith("STATUS:"):
            status = line.split(":", 1)[1].strip().lower()
        elif upper.startswith("MCQ:"):
            mcq_marks = parse_float(line.split(":", 1)[1], "MCQ marks")
        elif upper.startswith("SHORT_ANSWER:"):
            short_answer_marks = parse_float(
                line.split(":", 1)[1], "SHORT_ANSWER marks"
            )
        elif upper.startswith("TOTAL_MARKS:"):
            declared_total = parse_float(
                line.split(":", 1)[1], "TOTAL_MARKS"
            )
        elif ("QUESTION_NUMBER" in upper and "TYPE" in upper
              and "CORRECT_ANSWER" in upper):
            header_index = index
            break

    if not assessment_id:
        raise MarkingSchemeImportError("ASSESSMENT_ID is required.")
    if status != "locked":
        raise MarkingSchemeImportError(
            "STATUS must be 'locked' before grading."
        )
    if mcq_marks is None:
        raise MarkingSchemeImportError("MCQ marks are required. Add 'MCQ: 1'.")
    if short_answer_marks is None:
        raise MarkingSchemeImportError(
            "SHORT_ANSWER marks are required. Add 'SHORT_ANSWER: 2'."
        )
    if header_index is None:
        raise MarkingSchemeImportError(
            "Could not find CSV header Question_Number,Type,Correct_Answer."
        )

    csv_text = "\n".join(lines[header_index:])
    reader = csv.DictReader(StringIO(csv_text))
    questions: list[QuestionMarkingScheme] = []
    seen: set[int] = set()

    for row_idx, row in enumerate(reader, start=1):
        question_raw = row.get("Question_Number") or row.get("question_number")
        type_raw = row.get("Type") or row.get("type") or ""
        answer_raw = row.get("Correct_Answer") or row.get("correct_answer") or ""
        if not question_raw:
            continue
        try:
            question_no = int(str(question_raw).strip())
        except ValueError as exc:
            raise MarkingSchemeImportError(
                f"Invalid Question_Number at CSV row {row_idx}."
            ) from exc
        if question_no < 1:
            raise MarkingSchemeImportError("Question numbers must be positive.")
        if question_no in seen:
            raise MarkingSchemeImportError(
                f"Duplicate question number: Q{question_no}."
            )
        seen.add(question_no)
        question_type_text = str(type_raw).strip().lower().replace("-", "_")
        answer = str(answer_raw).strip().strip('"')

        if question_type_text == "mcq":
            if not answer:
                raise MarkingSchemeImportError(
                    f"Q{question_no}: MCQ requires a correct answer."
                )
            question_type = "mcq"
            maximum = mcq_marks
            correct_answer = answer
            guidance = "Use the approved MCQ answer key."
        elif question_type_text in {"short_answer", "short answer"}:
            question_type = "subjective"
            maximum = short_answer_marks
            correct_answer = None
            guidance = answer or None
        else:
            raise MarkingSchemeImportError(
                f"Q{question_no}: unsupported question type '{type_raw}'."
            )

        questions.append(QuestionMarkingScheme(
            question_no=question_no,
            max_marks=maximum,
            question_type=question_type,
            correct_answer=correct_answer,
            criteria=[],
            evaluation_guidance=guidance,
        ))

    if not questions:
        raise MarkingSchemeImportError("No questions found in marking scheme TXT.")

    total = sum(q.max_marks for q in questions)
    if declared_total is not None and abs(total - declared_total) > 1e-6:
        raise MarkingSchemeImportError(
            f"TOTAL_MARKS={declared_total} does not match calculated total={total}."
        )

    return MarkingScheme(
        assessment_id=assessment_id,
        version=1,
        questions=questions,
        total_marks=total,
        status="locked",
        generated_by="teacher",
    )
