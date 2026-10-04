from backend.tools.database import DatabaseTool
from backend.tools.gmail import GmailTool


# ============================================================
# IMPORTANT
# ============================================================
# Put YOUR OWN Gmail address here for testing.
# Do NOT use a real student's email yet.
# ============================================================

TEST_EMAIL = "electrofact3@gmail.com"


print("\n========================================")
print("STEP 1: DATABASE")
print("========================================")

db = DatabaseTool()


# Create a dedicated test student
student_result = db.create_student(
    student_no="GMAIL_TEST_001",
    university_roll="GMAIL_TEST_001",
    name="TCO Test Student",
    email=TEST_EMAIL,
    phone="0000000000",
    address="TCO Test",
    class_level="TCO Test Class",
    section="TEST",
    course="AI & ML",
    semester="1",
    school_id="TCO_TEST",
)

# If student already exists, get it instead
if student_result.success:
    print("Test student created.")
    print("Student ID:", student_result.data["id"])

else:

    print(
        "Student creation returned:",
        student_result.error_message,
    )

    existing = db.get_student(
        email=TEST_EMAIL,
    )

    if not existing.success:
        print("Could not find test student.")
        raise SystemExit(1)

    print("Using existing test student.")

# ============================================================
# GET EMAILS FROM DATABASE
# ============================================================

print("\n========================================")
print("STEP 2: GET EMAILS FROM DATABASE")
print("========================================")

email_result = db.get_student_emails(
    school_id="TCO_TEST",
    class_level="TCO Test Class",
    section="TEST",
)

if not email_result.success:

    print(
        "Database email lookup failed:",
        email_result.error_message,
    )

    raise SystemExit(1)


recipients = email_result.data

print("Recipients from database:")
for email in recipients:
    print(" -", email)


# ============================================================
# STEP 3: SEND THROUGH GMAIL
# ============================================================

print("\n========================================")
print("STEP 3: GMAIL")
print("========================================")

gmail = GmailTool()


form_url = (
    "https://docs.google.com/forms/d/example-test-form"
)

email_body = f"""Hello,

This is a test email from TCO.

Your assessment is ready.

Assessment:
SQL Basics Test

Start Test:
{form_url}

Regards,
TCO
"""


gmail_result = gmail.execute(
    operation="email.send_bulk",
    recipients=recipients,
    subject="TCO - Assessment Test",
    body=email_body,
)


# ============================================================
# RESULT
# ============================================================

print("\n========================================")
print("FINAL RESULT")
print("========================================")

print("Success:", gmail_result.success)

if gmail_result.success:

    print(
        "Total recipients:",
        gmail_result.data.get(
            "total_recipients"
        ),
    )

    print(
        "Sent:",
        gmail_result.data.get(
            "sent_count"
        ),
    )

    print(
        "Failed:",
        gmail_result.data.get(
            "failed_count"
        ),
    )

    print("\nSent details:")

    for item in gmail_result.data.get(
        "sent",
        [],
    ):
        print(
            item["email"],
            "→",
            item["message_id"],
        )

    print("\nDATABASE → GMAIL TEST PASSED")

else:

    print(
        "Error Code:",
        gmail_result.error_code,
    )

    print(
        "Error:",
        gmail_result.error_message,
    )

    print("\nDATABASE → GMAIL TEST FAILED")