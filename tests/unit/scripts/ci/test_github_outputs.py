"""Tests for GitHub Actions output helpers."""

from __future__ import annotations

from scripts.ci.github_outputs import write_github_outputs


def test_write_github_outputs_redacts_sensitive_stdout_fallback(
    monkeypatch,
    capsys,
) -> None:
    """Local output fallback should not print secret-looking values."""
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)

    write_github_outputs(
        {
            "server_url": "https://example.com",
            "server_password": "super-secret",
        }
    )

    output = capsys.readouterr().out
    assert "server_url=https://example.com" in output
    assert "server_password=***REDACTED***" in output
    assert "super-secret" not in output
