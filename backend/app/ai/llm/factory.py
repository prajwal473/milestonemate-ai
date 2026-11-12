from app.ai.llm.base import LLMClient
from app.ai.llm.gemini import GeminiClient
from app.ai.llm.mock import MockClient
from app.core.config import settings


def get_llm_client() -> LLMClient:

    mode = settings.ai_mode.lower()
    provider = settings.llm_provider.lower()

    if mode == "mock":
        return MockClient()

    if mode == "live" and provider == "gemini":
        return GeminiClient()

    raise ValueError(
        f"Unsupported AI configuration: mode={mode}, provider={provider}"
    )	