"""Gates G1 and G3 over model-supplied tool arguments (WORKFLOW.md B6).

G3 covers the JSON Schema subset the registry actually emits — `type`,
`required`, `properties`, `enum`, `minimum`/`maximum`, `default`. Phase 2's
declaration generator stays inside this subset; if it grows past it, swap in
the `jsonschema` package here rather than widening this by hand.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# G1: a model-supplied tenant identifier is dropped, never honoured or even
# validated. Tenancy comes from the server-side session only.
TENANT_KEYS = frozenset(
    {"company_id", "company", "chatbot_id", "chatbot", "tenant_id", "tenant"}
)

_TYPES = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "object": dict,
    "array": list,
}


class ValidationFailed(Exception):
    def __init__(self, errors: list[dict]):
        super().__init__("; ".join(e["message"] for e in errors))
        self.errors = errors


def strip_tenant_keys(args: dict) -> tuple[dict, list[str]]:
    dropped = sorted(k for k in args if k in TENANT_KEYS)
    return {k: v for k, v in args.items() if k not in TENANT_KEYS}, dropped


def validate_arguments(schema: dict, args) -> dict:
    """Return the validated arguments (defaults filled, unknown keys dropped).

    Raises `ValidationFailed` with machine-readable errors naming the field, so
    the model's retry is informed rather than blind (B6).
    """
    if not isinstance(args, dict):
        raise ValidationFailed(
            [{"field": None, "code": "not_an_object", "message": "Arguments must be an object."}]
        )

    properties = schema.get("properties", {}) or {}
    errors: list[dict] = []
    validated: dict = {}

    for name in schema.get("required", []) or []:
        if args.get(name) in (None, ""):
            errors.append(
                {"field": name, "code": "required", "message": f"'{name}' is required."}
            )

    for name, value in args.items():
        spec = properties.get(name)
        if spec is None:
            # Undeclared keys are ignored, not errors: the model gains nothing
            # by sending them and the executor never sees them.
            continue
        # Providers often deliver JSON integers as floats (3.0).
        if spec.get("type") == "integer" and isinstance(value, float) and value.is_integer():
            value = int(value)
        error = _check(name, spec, value)
        if error:
            errors.append(error)
        else:
            validated[name] = value

    if errors:
        raise ValidationFailed(errors)

    for name, spec in properties.items():
        if name not in validated and "default" in spec:
            validated[name] = spec["default"]
    return validated


def _check(name: str, spec: dict, value) -> dict | None:
    expected = spec.get("type")
    if expected:
        py_type = _TYPES.get(expected)
        # bool is an int subclass; a model sending `true` for a count is wrong.
        is_bool = isinstance(value, bool)
        if py_type and (not isinstance(value, py_type) or (is_bool and expected != "boolean")):
            return {
                "field": name,
                "code": "wrong_type",
                "message": f"'{name}' must be of type {expected}.",
            }

    if "enum" in spec and value not in spec["enum"]:
        return {
            "field": name,
            "code": "not_allowed",
            "allowed": spec["enum"],
            "message": f"'{name}' must be one of {spec['enum']}.",
        }
    if "minimum" in spec and isinstance(value, (int, float)) and value < spec["minimum"]:
        return {
            "field": name,
            "code": "below_minimum",
            "minimum": spec["minimum"],
            "message": f"'{name}' must be >= {spec['minimum']}.",
        }
    if "maximum" in spec and isinstance(value, (int, float)) and value > spec["maximum"]:
        return {
            "field": name,
            "code": "above_maximum",
            "maximum": spec["maximum"],
            "message": f"'{name}' must be <= {spec['maximum']}.",
        }
    return None
