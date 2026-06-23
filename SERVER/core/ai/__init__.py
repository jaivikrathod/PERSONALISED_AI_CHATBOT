"""Pluggable AI provider abstraction (embeddings + chat completions).

Public API::

    from core.ai import get_embedding_provider, get_llm_provider

    vec = get_embedding_provider().embed_query("How do I reset my password?")
    answer = get_llm_provider().chat(system="...", messages=[...])

Providers are selected from settings (EMBEDDING_PROVIDER / LLM_PROVIDER) and are
cached per-process. Adding a new provider = subclass + register in the factory.
"""

from .factory import get_embedding_provider, get_llm_provider

__all__ = ["get_embedding_provider", "get_llm_provider"]
