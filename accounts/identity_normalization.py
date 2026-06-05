from __future__ import annotations

import re
import unicodedata

_SPACE_RE = re.compile(r"\s+")
_LOOKUP_RE = re.compile(r"[^a-z0-9\s]+")
_EMPLOYEE_CODE_RE = re.compile(r"[^a-z0-9._\-/]+")


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_lookup_value(value: str) -> str:
    text = strip_accents(str(value or "")).lower().strip()
    text = _LOOKUP_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()


def normalize_employee_code(value: str) -> str:
    text = strip_accents(str(value or "")).lower().strip()
    return _EMPLOYEE_CODE_RE.sub("", text)


def build_initials(value: str) -> str:
    tokens = normalize_lookup_value(value).split()
    return "".join(token[0] for token in tokens if token)
