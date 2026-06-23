"""Abstract provider interfaces.

These define the contract every concrete provider must honour, so the rest of
the platform never imports a vendor SDK directly.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ChatMessage:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class ChatResult:
    content: str
    raw: dict = field(default_factory=dict)
    model: str = ""


class BaseEmbeddingProvider(ABC):
    """Turns text into fixed-length float vectors."""

    #: Output dimensionality of this provider's model. Must match EMBEDDING_DIM
    #: / the pgvector column width.
    dimension: int = 0

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a single string."""

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed many strings (batched) — order preserved."""


class BaseLLMProvider(ABC):
    """Generates a chat completion given a system prompt + message history."""

    @abstractmethod
    def chat(self, system: str, messages: list[ChatMessage], **kwargs) -> ChatResult:
        ...
