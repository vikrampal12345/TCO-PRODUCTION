from backend.tools.gmail import GmailTool


print("Starting Gmail test...")

# IMPORTANT:
# Yahan apna khud ka Gmail address daalo.
TEST_RECIPIENT = "electrofact3@gmail.com"


tool = GmailTool()

print("GmailTool created.")
print("Sending test email...")


result = tool.execute(
    operation="email.send",
    to=TEST_RECIPIENT,
    subject="TCO Gmail Tool Test",
    body=(
        "Hello,\n\n"
        "This is a test email sent by TCO "
        "using the Gmail API.\n\n"
        "Regards,\n"
        "TCO"
    ),
)


print("\n========================================")
print("GMAIL TEST RESULT")
print("========================================")

print("Success:", result.success)


if result.success:

    print(
        "Message ID:",
        result.data.get("message_id"),
    )

    print(
        "Thread ID:",
        result.data.get("thread_id"),
    )

    print(
        "Recipient:",
        result.data.get("to"),
    )

    print("\nGMAIL TEST PASSED")

else:

    print(
        "Error Code:",
        result.error_code,
    )

    print(
        "Error:",
        result.error_message,
    )

    print("\nGMAIL TEST FAILED")