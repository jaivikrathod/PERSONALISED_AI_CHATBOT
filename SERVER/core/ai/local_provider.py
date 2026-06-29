"""Local, key-free providers.

* ``MiniLMEmbeddingProvider`` - embeds text with the ``all-MiniLM-L6-v2``
  Sentence-Transformers model (384-dim). Runs fully offline on CPU; no API key.
  The heavy model is loaded once per process and cached.

* ``LocalLLMProvider`` - a deterministic, key-free "LLM" that simply returns the
  best-matching FAQ answer from the retrieved context. It lets the whole RAG
  chat flow work end-to-end without any external API. Swap ``LLM_PROVIDER`` to
  ``openai`` / ``gemini`` (with a key) to get generative phrasing instead.
"""

import logging
import threading

from django.conf import settings

from core.exceptions import ProviderError

from .base import BaseEmbeddingProvider, BaseLLMProvider, ChatMessage, ChatResult

logger = logging.getLogger(__name__)

# Process-wide singleton for the SentenceTransformer model. Loading it is
# expensive (hundreds of MB, several seconds) so we do it lazily exactly once
# and guard against races between concurrent requests/threads.
_model = None
_model_lock = threading.Lock()


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                try:
                    from sentence_transformers import SentenceTransformer
                except ImportError as exc:  # pragma: no cover - dependency guard
                    raise ProviderError(
                        "sentence-transformers is not installed. Run "
                        "`pip install sentence-transformers` to use the local "
                        "embedding provider."
                    ) from exc
                model_name = settings.EMBEDDING_MODEL_NAME
                logger.info("Loading embedding model '%s' (first use)…", model_name)
                _model = SentenceTransformer(model_name)
    return _model


class MiniLMEmbeddingProvider(BaseEmbeddingProvider):
    """all-MiniLM-L6-v2 embeddings (384-dim), computed locally on CPU."""

    dimension = 384

    def __init__(self):
        self.model = settings.EMBEDDING_MODEL_NAME

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            vectors = _get_model().encode(
                list(texts),
                normalize_embeddings=True,  # unit vectors -> clean cosine scores
                convert_to_numpy=True,
            )
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalise model errors
            logger.exception("MiniLM embedding failed")
            raise ProviderError(f"Local embedding failed: {exc}") from exc
        return [vec.tolist() for vec in vectors]


class LocalLLMProvider(BaseLLMProvider):
    """Key-free answerer: returns the top retrieved FAQ answer verbatim.

    ``ChatService`` passes the retrieved ``sources`` through ``**kwargs`` so we
    can echo the best-matching answer without calling any external service.
    """

    model = "local-extractive"

    def chat(self, system: str, messages: list[ChatMessage], **kwargs) -> ChatResult:
        sources = kwargs.get("sources") or []
        if sources:
            answer = sources[0].get("answer", "").strip()
            if answer:
                return ChatResult(content=answer, model=self.model)
        return ChatResult(
            content=(
                "I'm not sure about that yet, but I can connect you with a human "
                "agent who can help."
            ),
            model=self.model,
        )
