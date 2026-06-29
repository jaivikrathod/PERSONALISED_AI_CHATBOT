"""Provider registry + factory.

`get_embedding_provider()` / `get_llm_provider()` resolve the configured
provider, instantiate it once, and cache it. Register new providers by adding
to the maps below — nothing else in the codebase needs to change.
"""

from functools import lru_cache

from django.conf import settings

from core.exceptions import ProviderError

from .base import BaseEmbeddingProvider, BaseLLMProvider

_EMBEDDING_PROVIDERS = {
    "minilm": "core.ai.local_provider.MiniLMEmbeddingProvider",
    "openai": "core.ai.openai_provider.OpenAIEmbeddingProvider",
    "gemini": "core.ai.gemini_provider.GeminiEmbeddingProvider",
}

_LLM_PROVIDERS = {
    "local": "core.ai.local_provider.LocalLLMProvider",
    "openai": "core.ai.openai_provider.OpenAILLMProvider",
    "gemini": "core.ai.gemini_provider.GeminiLLMProvider",
}


def _import_class(path: str):
    module_path, _, cls_name = path.rpartition(".")
    from importlib import import_module

    return getattr(import_module(module_path), cls_name)


@lru_cache(maxsize=None)
def get_embedding_provider(name: str | None = None) -> BaseEmbeddingProvider:
    name = (name or settings.EMBEDDING_PROVIDER).lower()
    if name not in _EMBEDDING_PROVIDERS:
        raise ProviderError(f"Unknown embedding provider: {name}")
    return _import_class(_EMBEDDING_PROVIDERS[name])()


@lru_cache(maxsize=None)
def get_llm_provider(name: str | None = None) -> BaseLLMProvider:
    name = (name or settings.LLM_PROVIDER).lower()
    if name not in _LLM_PROVIDERS:
        raise ProviderError(f"Unknown LLM provider: {name}")
    return _import_class(_LLM_PROVIDERS[name])()
