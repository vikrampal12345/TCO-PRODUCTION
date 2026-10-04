from functools import lru_cache

from langchain_openai import ChatOpenAI


@lru_cache(maxsize=1)
def get_chat_model() -> ChatOpenAI:
    """
    Return the shared TCO chat model.

    Currently uses Qwen3 through LM Studio's
    OpenAI-compatible local API.

    Future production models can be switched here
    without changing agent code.
    """

    return ChatOpenAI(
        model="qwen/qwen3-4b-2507",
        base_url="http://127.0.0.1:1234/v1",
        api_key="lm-studio",
        temperature=0,
    )


