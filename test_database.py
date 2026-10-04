from backend.tools.database import DatabaseTool


db = DatabaseTool()

print("\n================================")
print("DATABASE INITIALIZATION")
print("================================")

print(
    "Database:",
    db.database_path,
)


# ============================================================
# CREATE STUDENT
# ============================================================

print("\n================================")
print("CREATE STUDENT")
print("================================")

student_result = db.create_student(
    student_no="STU001",
    university_roll="AKTU2026001",
    name="Rahul Sharma",
    email="rahul@example.com",
    phone="9876543210",
    address="Ghaziabad, Uttar Pradesh",
    class_level="BTech 1st Year",
    section="A",
    course="AI & ML",
    semester="1",
    school_id="TCO_DEMO",
)

print("Success:", student_result.success)
print("Student:", student_result.data)


if not student_result.success:
    print("Error:", student_result.error_message)
    raise SystemExit(1)


student_id = student_result.data["id"]


# ============================================================
# GET STUDENT
# ============================================================

print("\n================================")
print("GET STUDENT")
print("================================")

result = db.get_student(
    student_id=student_id,
)

print(result.data)


# ============================================================
# CREATE ASSESSMENT
# ============================================================

print("\n================================")
print("CREATE ASSESSMENT")
print("================================")

questions = [
    {
        "question_number": 1,
        "question": "What does SQL stand for?",
        "options": [
            "Structured Query Language",
            "Simple Query Language",
            "Standard Query Logic",
            "System Query Language",
        ],
        "correct_option": 1,
        "marks": 1,
    },
    {
        "question_number": 2,
        "question": "Which SQL command retrieves data?",
        "options": [
            "INSERT",
            "SELECT",
            "UPDATE",
            "DELETE",
        ],
        "correct_option": 2,
        "marks": 1,
    },
]

assessment_result = db.create_assessment(
    title="SQL Basics Test",
    questions=questions,
    subject="DBMS",
    chapter="SQL",
    topic="SQL Basics",
    class_level="BTech 1st Year",
    section="A",
    total_marks=2,
    generation_mode="llm_generated",
    form_id="demo_form_123",
    responder_url="https://example.com/form",
    status="published",
    created_by="teacher_001",
    school_id="TCO_DEMO",
)

print("Success:", assessment_result.success)
print("Assessment:", assessment_result.data)


if not assessment_result.success:
    print("Error:", assessment_result.error_message)
    raise SystemExit(1)


assessment_id = assessment_result.data[
    "assessment_id"
]


# ============================================================
# CREATE ATTEMPT + RESPONSES
# ============================================================

print("\n================================")
print("CREATE TEST RESULT")
print("================================")

attempt_result = db.create_attempt(
    assessment_id=assessment_id,
    student_id=student_id,
    score=2,
    max_score=2,
    status="submitted",
    responses=[
        {
            "question_id": 1,
            "selected_option": 1,
            "is_correct": True,
            "marks_awarded": 1,
        },
        {
            "question_id": 2,
            "selected_option": 2,
            "is_correct": True,
            "marks_awarded": 1,
        },
    ],
)

print("Success:", attempt_result.success)
print("Attempt:", attempt_result.data)


# ============================================================
# FETCH STUDENT RESULTS
# ============================================================

print("\n================================")
print("STUDENT RESULTS")
print("================================")

results = db.get_student_results(
    student_id=student_id,
)

print(results.data)


print("\n================================")
print("DATABASE TEST PASSED")
print("================================")