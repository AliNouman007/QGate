from __future__ import annotations

from collections.abc import Mapping

_REDACTED = "<redacted>"
_SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "set-cookie",
    "password",
    "passwd",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "apikey",
    "card_number",
    "cardnumber",
    "cvv",
    "cvc",
    "bank_account",
}


def is_sensitive_key(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    return normalized in _SENSITIVE_KEYS or any(
        marker in normalized
        for marker in ("password", "secret", "token", "authorization", "cookie", "card", "cvv")
    )


def redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {key: (_REDACTED if is_sensitive_key(key) else value) for key, value in headers.items()}


def redact_mapping(values: Mapping[str, object]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in values.items():
        if is_sensitive_key(key):
            result[key] = _REDACTED
        elif isinstance(value, Mapping):
            result[key] = redact_mapping({str(k): v for k, v in value.items()})
        else:
            result[key] = value
    return result


def redact_url(url: str) -> str:
    if "?" not in url:
        return url
    base, query = url.split("?", 1)
    safe_parts: list[str] = []
    for part in query.split("&"):
        key, sep, value = part.partition("=")
        safe_parts.append(f"{key}{sep}{_REDACTED if is_sensitive_key(key) else value}")
    return base + "?" + "&".join(safe_parts)
