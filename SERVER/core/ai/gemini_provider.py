"""Google Gemini-backed embedding + chat providers."""

import logging

from django.conf import settings

from core.exceptions import ProviderError

from .base import BaseEmbeddingProvider, BaseLLMProvider, ChatMessage, ChatResult

logger = logging.getLogger(__name__)


def _configure():
    import google.generativeai as genai

    if not settings.GEMINI_API_KEY:
        raise ProviderError("GEMINI_API_KEY is not configured.")
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    dimension = settings.EMBEDDING_DIM

    def __init__(self):
        self.model = settings.GEMINI_EMBEDDING_MODEL

    def embed_query(self, text: str) -> list[float]:
        genai = _configure()
        try:
            resp = genai.embed_content(
                model=self.model, content=text, task_type="retrieval_query"
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Gemini embedding failed")
            raise ProviderError(f"Gemini embedding failed: {exc}") from exc
        return resp["embedding"]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        genai = _configure()
        try:
            resp = genai.embed_content(
                model=self.model, content=texts, task_type="retrieval_document"
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Gemini batch embedding failed")
            raise ProviderError(f"Gemini batch embedding failed: {exc}") from exc
        emb = resp["embedding"]
        # SDK returns a single vector for str input, list for list input.
        return emb if isinstance(emb[0], list) else [emb]


class GeminiLLMProvider(BaseLLMProvider):
    def __init__(self):
        self.model_name = settings.GEMINI_CHAT_MODEL

    def chat(self, system: str, messages: list[ChatMessage], **kwargs) -> ChatResult:
        genai = _configure()
        history = []
        for m in messages:
            role = "model" if m.role == "assistant" else "user"
            history.append({"role": role, "parts": [m.content]})
        try:
            model = genai.GenerativeModel(self.model_name, system_instruction=system)
            resp = model.generate_content(history)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Gemini chat failed")
            raise ProviderError(f"Gemini chat failed: {exc}") from exc

        return ChatResult(content=resp.text or "", model=self.model_name)
