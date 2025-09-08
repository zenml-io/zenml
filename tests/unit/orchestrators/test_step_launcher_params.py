"""Unit tests for StepLauncher request parameter validation/merge.

These tests verify allowlisting, simple type coercion, and size caps when
merging request parameters into the effective step configuration in serving.
"""

from zenml.orchestrators.step_launcher import StepLauncher


def test_validate_and_merge_request_params_allowlist_and_types(monkeypatch):
    """Allowlist known params and coerce simple types; drop unknowns."""
    # Use the real method by binding to a StepLauncher instance with minimal init
    sl = StepLauncher.__new__(StepLauncher)  # type: ignore

    class Cfg:
        def __init__(self):
            self.parameters = {"city": "paris", "count": 1}

    effective = Cfg()
    req = {
        "city": "munich",  # allowed, string
        "count": "2",  # allowed, coercible to int
        "unknown": "drop-me",  # not declared
    }

    merged = StepLauncher._validate_and_merge_request_params(
        sl, req, effective
    )
    assert merged["city"] == "munich"
    assert merged["count"] == 2
    assert "unknown" not in merged


def test_validate_and_merge_request_params_size_caps(monkeypatch):
    """Drop oversized string/collection parameters per safety caps."""
    sl = StepLauncher.__new__(StepLauncher)  # type: ignore

    class Cfg:
        def __init__(self):
            self.parameters = {"text": "ok"}

    effective = Cfg()
    big = "x" * 20000  # 20KB string -> dropped
    req = {"text": big}
    merged = StepLauncher._validate_and_merge_request_params(
        sl, req, effective
    )
    # Should keep the default, drop oversize
    assert merged["text"] == "ok"
