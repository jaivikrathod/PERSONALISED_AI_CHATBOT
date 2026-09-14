"""The provider seam (WORKFLOW.md D4): declarations in, tool calls out.

Deliberately small. The orchestrator speaks only these dataclasses; a provider
translates them to and from its own wire format. Nothing here knows about
Django, tenants or tools-as-rows.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class ProviderError(Exception):
    """The model could not be reached or returned something unusable."""


@dataclass
class ToolCall:
    name: str
    args: dict[str, Any]
    id: str = ""
    # Opaque provider data that must be replayed with the call (e.g. Gemini's
    # thought signature). Persisted, never interpreted by the orchestrator.
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class HistoryItem:
    """One replayed message. Exactly one of text / tool_call / tool_result."""

    role: str  # "user" | "assistant" | "tool"
    text: str = ""
    tool_call: ToolCall | None = None
    tool_name: str = ""
    tool_call_id: str = ""
    tool_result: Any = None


@dataclass
class ModelResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tokens: int | None = None


class ChatProvider(ABC):
    @abstractmethod
    def generate(
        self,
        *,
        system: str,
        history: list[HistoryItem],
        tools: list[dict],
        model: str,
        temperature: float,
    ) -> ModelResponse:
        """One model round trip. `tools` are `Tool.declaration()` dicts.

        An empty `tools` list means tools are withheld: the model must answer
        in text (B5 budget degradation).
        """
        raise NotImplementedError
