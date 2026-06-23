"""OpenAI-backed embedding + chat providers."""

import logging

from django.conf import settings

from core.exceptions import ProviderError

from .base import BaseEmbeddingProvider, BaseLLMProvider, ChatMessage, ChatResult

logger = logging.getLogger(__name__)


def _client():
    from openai import OpenAI

    if not settings.OPENAI_API_KEY:
        raise ProviderError("OPENAI_API_KEY is not configured.")
    return OpenAI(api_key=settings.OPENAI_API_KEY)


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    dimension = settings.EMBEDDING_DIM

    def __init__(self):
        self.model = settings.OPENAI_EMBEDDING_MODEL

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            resp = _client().embeddings.create(model=self.model, input=texts)
        except Exception as exc:  # noqa: BLE001 - normalise vendor errors
            logger.exception("OpenAI embedding failed")
            raise ProviderError(f"OpenAI embedding failed: {exc}") from exc
        # Preserve input order.
        return [item.embedding for item in sorted(resp.data, key=lambda d: d.index)]


class OpenAILLMProvider(BaseLLMProvider):
    def __init__(self):
        self.model = settings.OPENAI_CHAT_MODEL

    def chat(self, system: str, messages: list[ChatMessage], **kwargs) -> ChatResult:
        payload = [{"role": "system", "content": system}]
        payload += [{"role": m.role, "content": m.content} for m in messages]
        try:
            resp = _client().chat.completions.create(
                model=self.model,
                messages=payload,
                temperature=kwargs.get("temperature", 0.2),
                max_tokens=kwargs.get("max_tokens", 600),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("OpenAI chat failed")
            raise ProviderError(f"OpenAI chat failed: {exc}") from exc

        return ChatResult(
            content=resp.choices[0].message.content or "",
            model=self.model,
            raw={"id": getattr(resp, "id", "")},
        )
