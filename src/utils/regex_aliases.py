"""Central registry for predefined regex pattern aliases."""

from __future__ import annotations


REGEX_ALIASES = {
    "EMAIL": r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    "PHONE": r"^\+?[\d\s().-]{7,}$",
    "URL": r"^https?://[^\s/$.?#].[^\s]*$",
    "PINCODE": r"^\d{5,6}$",
}


def resolve_regex_pattern(pattern: str) -> str:
    """Return the regex for a predefined alias or the supplied raw pattern."""

    return REGEX_ALIASES.get(pattern.upper(), pattern)
