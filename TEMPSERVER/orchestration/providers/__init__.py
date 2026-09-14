from django.conf import settings

from .base import ChatProvider, HistoryItem, ModelResponse, ProviderError, ToolCall

__all__ = [
    "ChatProvider",
    "HistoryItem",
    "ModelResponse",
    "ProviderError",
    "ToolCall",
    "get_provider",
]


def get_provider() -> ChatProvider:
    name = getattr(settings, "CHAT_PROVIDER", "gemini")
    if name == "gemini":
        from .gemini import GeminiProvider

        return GeminiProvider()
    raise ProviderError(f"Unknown CHAT_PROVIDER {name!r}.")
