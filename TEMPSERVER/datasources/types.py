"""Field data types, operators, coercion and type inference.

Coercion runs at import so `payload` holds typed JSON (numbers as numbers,
dates as ISO strings). That is what lets the `records` adapter cast with a
plain `::double precision` — the same expression the publish-time index is
built on — instead of guarding every comparison.
"""

from __future__ import annotations

import datetime as dt
import re

STRING = "string"
INTEGER = "integer"
NUMBER = "number"
BOOLEAN = "boolean"
DATE = "date"
DATETIME = "datetime"
STRING_ARRAY = "string_array"

DATA_TYPE_CHOICES = [
    (STRING, "Text"),
    (INTEGER, "Whole number"),
    (NUMBER, "Number"),
    (BOOLEAN, "Yes / no"),
    (DATE, "Date"),
    (DATETIME, "Date and time"),
    (STRING_ARRAY, "List of values"),
]

EQUALS = "equals"
ILIKE = "ilike"
GTE = "gte"
LTE = "lte"
CONTAINS_ANY = "contains_any"

# Which operators make sense for a type at all. `allowed_operators` on a field
# must be a subset (G5).
OPERATORS_BY_TYPE = {
    STRING: [EQUALS, ILIKE],
    INTEGER: [EQUALS, GTE, LTE],
    NUMBER: [EQUALS, GTE, LTE],
    BOOLEAN: [EQUALS],
    DATE: [GTE, LTE],
    DATETIME: [GTE, LTE],
    STRING_ARRAY: [CONTAINS_ANY],
}

NUMERIC_TYPES = (INTEGER, NUMBER)
ORDERED_TYPES = (INTEGER, NUMBER, DATE, DATETIME)

# B3: a string with at most this many distinct values becomes an enum.
ENUM_MAX_CARDINALITY = 50

ARRAY_SEPARATORS = (";", "|")
TRUE_WORDS = {"true", "yes", "y", "t"}
FALSE_WORDS = {"false", "no", "n", "f"}
DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y")

# Column-name parts that start hidden. A suggestion the company reviews, not a
# guarantee — the field-permissions review is the real control.
SENSITIVE_PARTS = {
    "phone", "mobile", "email", "cost", "margin", "supplier", "owner",
    "internal", "password", "secret", "token", "salary", "commission",
}


class CoercionError(ValueError):
    pass


def default_operators(data_type: str, cardinality: int | None = None) -> list[str]:
    if data_type == STRING:
        if cardinality is not None and cardinality <= ENUM_MAX_CARDINALITY:
            return [EQUALS]
        return [ILIKE]
    if data_type == NUMBER:
        return [GTE, LTE]
    return list(OPERATORS_BY_TYPE[data_type])


def is_sensitive(name: str) -> bool:
    return bool(SENSITIVE_PARTS & set(name.split("_")))


def normalise_header(header: str, taken: set[str]) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", str(header).strip().lower()).strip("_") or "column"
    if not slug[0].isalpha():
        slug = f"f_{slug}"
    slug = slug[:60]
    candidate, n = slug, 2
    while candidate in taken:
        candidate = f"{slug}_{n}"
        n += 1
    taken.add(candidate)
    return candidate


def is_blank(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip()) or value == []


def coerce(value, data_type: str):
    """Cast one raw value to `data_type`. Blank → None. Raises CoercionError."""
    if is_blank(value):
        return None
    if isinstance(value, dict):
        raise CoercionError("nested objects are not supported")

    if data_type == STRING:
        if isinstance(value, list):
            raise CoercionError("expected a single value, got a list")
        return str(value).strip()

    if data_type in NUMERIC_TYPES:
        if isinstance(value, bool) or isinstance(value, list):
            raise CoercionError(f"{value!r} is not a number")
        if isinstance(value, (int, float)):
            number = value
        else:
            text = re.sub(r"[,_\s]", "", str(value))
            try:
                number = float(text)
            except ValueError:
                raise CoercionError(f"{value!r} is not a number") from None
        if data_type == INTEGER:
            if float(number) != int(float(number)):
                raise CoercionError(f"{value!r} is not a whole number")
            return int(float(number))
        return int(number) if float(number).is_integer() else float(number)

    if data_type == BOOLEAN:
        if isinstance(value, bool):
            return value
        if isinstance(value, int) and value in (0, 1):
            return bool(value)
        text = str(value).strip().lower()
        if text in TRUE_WORDS or text == "1":
            return True
        if text in FALSE_WORDS or text == "0":
            return False
        raise CoercionError(f"{value!r} is not yes/no")

    if data_type == DATE:
        if isinstance(value, dt.datetime):
            return value.date().isoformat()
        if isinstance(value, dt.date):
            return value.isoformat()
        text = str(value).strip()
        for fmt in DATE_FORMATS:
            try:
                return dt.datetime.strptime(text, fmt).date().isoformat()
            except ValueError:
                continue
        raise CoercionError(f"{value!r} is not a date (use YYYY-MM-DD)")

    if data_type == DATETIME:
        try:
            parsed = value if isinstance(value, dt.datetime) else dt.datetime.fromisoformat(
                str(value).strip().replace("Z", "+00:00")
            )
        except ValueError:
            raise CoercionError(f"{value!r} is not a date and time (use ISO 8601)") from None
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)
        # One fixed format, so stored values compare correctly as text.
        return parsed.isoformat(timespec="seconds")

    if data_type == STRING_ARRAY:
        if isinstance(value, list):
            items = value
        else:
            text = str(value)
            separator = next((s for s in ARRAY_SEPARATORS if s in text), None)
            items = text.split(separator) if separator else [text]
        cleaned = [str(item).strip() for item in items if not is_blank(item)]
        return cleaned or None

    raise CoercionError(f"unknown data type {data_type!r}")


def infer_type(values: list) -> str:
    """Suggest a type from a sample of non-blank values."""
    values = [v for v in values if not is_blank(v)]
    if not values:
        return STRING

    if all(isinstance(v, bool) for v in values):
        return BOOLEAN
    if all(isinstance(v, list) for v in values):
        return STRING_ARRAY
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
        return INTEGER if all(float(v).is_integer() for v in values) else NUMBER

    texts = [str(v).strip() for v in values]
    if all(t.lower() in TRUE_WORDS | FALSE_WORDS for t in texts):
        return BOOLEAN
    # Leading zeros are identifiers (pin codes, phone numbers), not numbers.
    if not any(len(t) > 1 and t.startswith("0") and t[1].isdigit() for t in texts):
        for candidate in (INTEGER, NUMBER):
            if _all_coerce(texts, candidate):
                return candidate
    for candidate in (DATE, DATETIME):
        if _all_coerce(texts, candidate):
            return candidate

    with_separator = [t for t in texts if any(s in t for s in ARRAY_SEPARATORS)]
    if len(with_separator) * 2 >= len(texts):
        pieces = [p for t in texts for p in re.split(r"[;|]", t)]
        if all(len(p.strip()) <= 40 for p in pieces):
            return STRING_ARRAY
    return STRING


def _all_coerce(texts: list[str], data_type: str) -> bool:
    try:
        for text in texts:
            coerce(text, data_type)
    except CoercionError:
        return False
    return True
