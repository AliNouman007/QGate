from qgate_browser_execution.redaction import redact_headers, redact_mapping, redact_url


def test_sensitive_headers_are_redacted() -> None:
    result = redact_headers({"Authorization": "Bearer secret", "Accept": "application/json"})
    assert result["Authorization"] == "<redacted>"
    assert result["Accept"] == "application/json"


def test_nested_sensitive_values_are_redacted() -> None:
    result = redact_mapping({"profile": {"password": "secret", "name": "qa"}})
    assert result == {"profile": {"password": "<redacted>", "name": "qa"}}


def test_sensitive_query_values_are_redacted() -> None:
    assert redact_url("https://example.test/cb?token=abc&mode=test") == (
        "https://example.test/cb?token=<redacted>&mode=test"
    )
