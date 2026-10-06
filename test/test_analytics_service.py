from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from backend.services.analytics_service import AnalyticsService
from backend.services.result_store import ResultStore


def create_test_db(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE students (
            id INTEGER PRIMARY KEY,
            student_no TEXT,
            university_roll TEXT,
            name TEXT,
            email TEXT,
            class_level TEXT,
            section TEXT,
            school_id TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE assessments (
            id INTEGER PRIMARY KEY,
            title TEXT,
            subject TEXT,
            chapter TEXT,
            topic TEXT,
            class_level TEXT,
            section TEXT,
            school_id TEXT,
            total_marks REAL,
            test_date TEXT,
            form_id TEXT,
            responder_url TEXT,
            status TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE assessment_attempts (
            id INTEGER PRIMARY KEY,
            assessment_id INTEGER,
            student_id INTEGER,
            attempt_number INTEGER,
            student_name TEXT,
            student_email TEXT,
            started_at TEXT,
            submitted_at TEXT,
            obtained_marks REAL,
            total_marks REAL,
            percentage REAL,
            correct_answers INTEGER,
            wrong_answers INTEGER,
            unanswered INTEGER,
            status TEXT,
            form_response_id TEXT,
            answers_json TEXT,
            question_results_json TEXT,
            result_email_status TEXT,
            result_email_sent_at TEXT,
            result_email_error TEXT,
            created_at TEXT,
            updated_at TEXT,
            UNIQUE (assessment_id, student_id, attempt_number)
        )
        """
    )

    connection.execute(
        """
        CREATE VIEW student_result_view AS
        SELECT
            aa.id AS result_id,
            aa.assessment_id,
            aa.student_id,
            aa.attempt_number,
            s.student_no,
            s.university_roll,
            s.name AS student_name,
            s.email AS student_email,
            s.class_level AS student_class_level,
            s.section AS student_section,
            s.school_id AS student_school_id,
            a.title AS assessment_title,
            a.subject,
            a.chapter,
            a.topic,
            a.class_level AS assessment_class_level,
            a.section AS assessment_section,
            a.test_date,
            a.total_marks AS assessment_total_marks,
            a.form_id,
            a.responder_url,
            a.status AS assessment_status,
            aa.started_at,
            aa.submitted_at,
            aa.obtained_marks,
            aa.total_marks,
            aa.percentage,
            aa.correct_answers,
            aa.wrong_answers,
            aa.unanswered,
            aa.status AS result_status,
            aa.form_response_id,
            aa.answers_json,
            aa.question_results_json,
            aa.result_email_status,
            aa.result_email_sent_at,
            aa.result_email_error,
            aa.created_at AS result_created_at,
            aa.updated_at AS result_updated_at
        FROM assessment_attempts aa
        JOIN students s ON s.id = aa.student_id
        JOIN assessments a ON a.id = aa.assessment_id
        """
    )

    connection.execute(
        """
        INSERT INTO students (
            id, student_no, university_roll, name, email,
            class_level, section, school_id
        )
        VALUES
            (1, 'R001', 'R001', 'Rahul Sharma',
             'rahul@example.com', 'TCO Test Class', 'TEST', 'TCO_TEST'),
            (2, 'E001', 'E001', 'electro',
             'electro@example.com', 'TCO Test Class', 'TEST', 'TCO_TEST')
        """
    )

    connection.execute(
        """
        INSERT INTO assessments (
            id, title, subject, chapter, topic, class_level,
            section, school_id, total_marks, test_date,
            form_id, responder_url, status
        )
        VALUES (
            20,
            'TCO - Test Assessment',
            'Computer Organization',
            'Unit 2',
            'Booth Algorithm',
            'BTech 1st Year',
            '',
            'TCO_TEST',
            20,
            NULL,
            'TEST_FORM',
            '',
            'published'
        )
        """
    )

    connection.execute(
        """
        INSERT INTO assessment_attempts (
            id, assessment_id, student_id, attempt_number,
            student_name, student_email, submitted_at,
            obtained_marks, total_marks, percentage,
            correct_answers, wrong_answers, unanswered,
            status, form_response_id, answers_json,
            question_results_json, result_email_status,
            result_email_sent_at, result_email_error,
            created_at, updated_at
        )
        VALUES
            (
                1, 20, 1, 1,
                'Rahul Sharma', 'rahul@example.com',
                '2026-10-06T05:00:00Z',
                8, 20, 40,
                2, 3, 0,
                'evaluated', 'R1', '[]', '[]',
                'not_sent', NULL, NULL,
                '2026-10-06T05:00:00Z',
                '2026-10-06T05:00:00Z'
            ),
            (
                2, 20, 2, 1,
                'electro', 'electro@example.com',
                '2026-10-06T05:01:00Z',
                16, 20, 80,
                4, 1, 0,
                'evaluated', 'R2', '[]', '[]',
                'not_sent', NULL, NULL,
                '2026-10-06T05:01:00Z',
                '2026-10-06T05:01:00Z'
            )
        """
    )

    connection.commit()
    connection.close()


def main() -> None:
    temp_dir = Path(
        tempfile.mkdtemp(prefix="tco_analytics_service_")
    )
    db_path = temp_dir / "analytics_test.db"
    create_test_db(db_path)

    service = AnalyticsService(
        result_store=ResultStore(db_path=db_path)
    )

    below_10 = service.filter_students(
        school_id="TCO_TEST",
        max_marks=10,
    )
    assert len(below_10) == 1
    assert below_10[0]["student_name"] == "Rahul Sharma"

    detail = service.get_student_detail(
        student_name="Rahul Sharma",
        school_id="TCO_TEST",
    )
    assert detail["found"] is True
    assert detail["result_count"] == 1
    assert detail["summary"]["latest_percentage"] == 40.0

    performance = service.get_class_performance(
        school_id="TCO_TEST",
    )
    assert performance["student_count"] == 2
    assert performance["summary"]["average_percentage"] == 60.0
    assert performance["summary"]["median_percentage"] == 60
    assert performance["summary"]["highest_percentage"] == 80.0
    assert performance["summary"]["lowest_percentage"] == 40.0
    assert performance["summary"]["pass_count"] == 2
    assert performance["summary"]["pass_rate"] == 100.0
    assert performance["score_distribution"]["21-40"] == 1
    assert performance["score_distribution"]["61-80"] == 1

    ranking = service.get_ranked_students(
        school_id="TCO_TEST",
        limit=2,
    )
    assert ranking[0]["student_name"] == "electro"
    assert ranking[0]["percentage"] == 80.0

    visualization = service.build_visualization_data(
        performance
    )
    assert len(visualization["student_performance"]) == 2
    assert len(visualization["score_distribution"]) == 5

    print("TCO ANALYTICS SERVICE TEST PASSED")
    print("Students <= 10 marks:", len(below_10))
    print(
        "Class average:",
        performance["summary"]["average_percentage"],
    )
    print(
        "Highest:",
        performance["summary"]["highest_percentage"],
    )
    print(
        "Distribution:",
        performance["score_distribution"],
    )


if __name__ == "__main__":
    main()
