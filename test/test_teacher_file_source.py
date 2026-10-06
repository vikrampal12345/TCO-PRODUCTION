import sys
from pathlib import Path

# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# IMPORT
# ============================================================

from backend.rag.source_retrieval import retrieve_source


# ============================================================
# TEST FILE
# ============================================================

TEST_FILE = PROJECT_ROOT / "data" / "documents" / "upload_test.txt"


# ============================================================
# CHECK TEST FILE EXISTS
# ============================================================

if not TEST_FILE.exists():
    print("\nERROR: Test document not found.")
    print(f"Expected file: {TEST_FILE}")
    sys.exit(1)


# ============================================================
# TEST STATE
# ============================================================

state = {
    "teacher_id": "TEST_TEACHER",
    "school_id": "TCO_TEST",
    "conversation_id": "upload_test",

    "teacher_request": "Create a test on Binary Search",

    "subject": "Computer Science",
    "chapter": "Searching",
    "topic": "Binary Search",

    "generation_mode": "source_grounded",
    "source_preference": "teacher_file",

    "uploaded_file_path": str(TEST_FILE),
}


# ============================================================
# RUN SOURCE RETRIEVAL
# ============================================================

print("\n==================================================")
print("TCO TEACHER FILE RAG TEST")
print("==================================================")

print(f"Test file: {TEST_FILE}")
print(f"File exists: {TEST_FILE.exists()}")

print("\nRunning retrieve_source()...\n")

try:
    result = retrieve_source(state)

except Exception as exc:
    print("==================================================")
    print("RUNTIME ERROR")
    print("==================================================")
    print(f"{type(exc).__name__}: {exc}")

    import traceback

    traceback.print_exc()

    sys.exit(1)


# ============================================================
# RESULT
# ============================================================

print("==================================================")
print("RESULT")
print("==================================================")

keys_to_print = [
    "status",
    "source_status",
    "source_available",
    "source_approved",
    "approval_required",
    "approval_status",
    "approval_type",
    "approved_by",
    "source",
    "uploaded_file_name",
    "uploaded_file_type",
    "uploaded_source_id",
    "knowledge_source",
    "next_action",
    "error_code",
    "error_message",
]

for key in keys_to_print:
    print(f"{key}: {result.get(key)}")


# ============================================================
# RETRIEVED CONTEXT
# ============================================================

print("\n==================================================")
print("RETRIEVED CONTEXT")
print("==================================================")

context = result.get("retrieved_context", "")

if context:
    print(context)
else:
    print("NO CONTEXT FOUND")


# ============================================================
# SOURCE REFERENCES
# ============================================================

print("\n==================================================")
print("SOURCE REFERENCES")
print("==================================================")

references = result.get("source_references", [])

if references:
    for reference in references:
        print(reference)
else:
    print("NO SOURCE REFERENCES")


# ============================================================
# SELECTED SOURCE
# ============================================================

print("\n==================================================")
print("SELECTED SOURCE")
print("==================================================")

selected_source = result.get("selected_source")

if selected_source:
    print(selected_source)
else:
    print("NO SELECTED SOURCE")


# ============================================================
# METADATA
# ============================================================

print("\n==================================================")
print("METADATA")
print("==================================================")

metadata = result.get("metadata", {})

if metadata:
    for key, value in metadata.items():
        print(f"{key}: {value}")
else:
    print("NO METADATA")


# ============================================================
# FINAL STATUS
# ============================================================

print("\n==================================================")
print("TEST COMPLETE")
print("==================================================")

if result.get("source_status") == "source_ready":
    print("SUCCESS: Teacher file was ingested and RAG context was retrieved.")

elif result.get("source_status") == "no_source_found":
    print("FAILED: No source was found.")

else:
    print(
        f"CHECK RESULT: source_status="
        f"{result.get('source_status')}"
    )