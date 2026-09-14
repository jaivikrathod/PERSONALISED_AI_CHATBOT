"""Gemini implementation of the provider seam.

The only module in the codebase that imports `google.genai` — pinned by
`tests/test_orchestration.py`.
"""

from __future__ import annotations

import base64
import logging

from django.conf import settings

from .base import ChatProvider, HistoryItem, ModelResponse, ProviderError, ToolCall

logger = logging.getLogger(__name__)


class GeminiProvider(ChatProvider):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY

    def generate(self, *, system, history, tools, model, temperature):
        from google import genai
        from google.genai import types

        if not self.api_key:
            raise ProviderError("GEMINI_API_KEY is not configured.")

        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            # The orchestrator owns the loop; the SDK must not run tools itself.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        )
        if tools:
            config.tools = [
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name=decl["name"],
                            description=decl["description"],
                            parameters_json_schema=decl["parameters"],
                        )
                        for decl in tools
                    ]
                )
            ]

        try:
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=model,
                contents=_to_contents(history, types),
                config=config,
            )
        except Exception as exc:  # network / auth / quota errors
            logger.exception("Gemini request failed")
            raise ProviderError(f"Error communicating with Gemini: {exc}") from exc

        return _from_response(response)


def _to_contents(history: list[HistoryItem], types):
    """Neutral history -> Gemini contents, merging adjacent same-role parts.

    Parallel tool calls are stored as separate rows but must reach Gemini as one
    model turn followed by one turn of function responses.
    """
    contents = []
    for item in history:
        if item.tool_call is not None:
            role = "model"
            part = types.Part(
                function_call=types.FunctionCall(
                    name=item.tool_call.name, args=item.tool_call.args
                )
            )
            signature = item.tool_call.meta.get("thought_signature")
            if signature:
                part.thought_signature = base64.b64decode(signature)
        elif item.role == "tool":
            role = "user"
            part = types.Part.from_function_response(
                name=item.tool_name,
                response={"output": item.tool_result},
            )
        else:
            role = "model" if item.role == "assistant" else "user"
            part = types.Part(text=item.text)

        if contents and contents[-1].role == role:
            contents[-1].parts.append(part)
        else:
            contents.append(types.Content(role=role, parts=[part]))
    return contents


def _from_response(response) -> ModelResponse:
    candidates = getattr(response, "candidates", None) or []
    parts = []
    if candidates and candidates[0].content and candidates[0].content.parts:
        parts = candidates[0].content.parts

    text_chunks, calls = [], []
    for part in parts:
        if part.function_call is not None:
            meta = {}
            if part.thought_signature:
                meta["thought_signature"] = base64.b64encode(
                    part.thought_signature
                ).decode()
            calls.append(
                ToolCall(
                    name=part.function_call.name or "",
                    args=dict(part.function_call.args or {}),
                    id=part.function_call.id or "",
                    meta=meta,
                )
            )
        elif part.text and not part.thought:
            text_chunks.append(part.text)

    usage = getattr(response, "usage_metadata", None)
    tokens = getattr(usage, "total_token_count", None) if usage else None
    return ModelResponse(text="".join(text_chunks).strip(), tool_calls=calls, tokens=tokens)
