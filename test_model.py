from backend.core.model_provider import get_chat_model


model = get_chat_model()

response = model.invoke(
    "Reply with exactly: TCO local LLM working"
)

print(response.content)