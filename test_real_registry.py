from backend.core.bootstrap import build_default_registry


registry = build_default_registry()

print("Assessment Agent:")
print(registry.get_agent("assessment.create").name)

print("\nAssessment Review Agent:")
print(registry.get_agent("assessment.review").name)

print("\nGoogle Forms Tool:")
print(registry.get_tool("form.create_quiz").name)

print("\nDatabase Tool:")
print(registry.get_tool("db.student.create").name)

print("\nDatabase Email Capability:")
print(registry.get_tool("db.student.get_emails").name)

print("\nGmail Tool:")
print(registry.get_tool("email.send").name)

print("\nBulk Gmail Capability:")
print(registry.get_tool("email.send_bulk").name)

print("\nDEFAULT REGISTRY TEST PASSED")