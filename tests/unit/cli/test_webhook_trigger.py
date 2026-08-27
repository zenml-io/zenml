"""Tests for provider-neutral webhook trigger CLI configuration."""

from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from click.testing import CliRunner

trigger_module = import_module("zenml.cli.trigger")


def test_webhook_trigger_help_describes_generic_configuration() -> None:
    """Create and update help expose the provider-neutral contract."""
    create_result = CliRunner().invoke(
        trigger_module.webhook.commands["create"], ["--help"]
    )
    update_result = CliRunner().invoke(
        trigger_module.webhook.commands["update"], ["--help"]
    )

    assert create_result.exit_code == 0, create_result.output
    assert update_result.exit_code == 0, update_result.output
    assert "target_events" in create_result.output
    assert "--webhook" in create_result.output
    assert "--config" in create_result.output
    assert "complete configuration" in update_result.output
    assert "--webhook-type" not in create_result.output


def test_create_webhook_trigger_loads_generic_config(
    monkeypatch, tmp_path: Path
) -> None:
    """Create passes a generic configuration and selected webhook."""
    calls = []

    class _Client:
        def create_webhook_trigger(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(id=uuid4())

    monkeypatch.setattr(trigger_module, "Client", _Client)
    config_path = tmp_path / "webhook.yaml"
    config_path.write_text(
        """
target_events:
  - type: push
    repo: zenml-io/zenml
    branch: main
""".lstrip()
    )

    result = CliRunner().invoke(
        trigger_module.webhook.commands["create"],
        [
            "github-trigger",
            "--webhook",
            "github-webhook",
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls[0]["webhook"] == "github-webhook"
    assert calls[0]["configuration"].target_events == [
        {
            "type": "push",
            "repo": "zenml-io/zenml",
            "branch": "main",
        }
    ]


def test_create_webhook_trigger_requires_webhook_and_config() -> None:
    """Create requires both ownership and configuration arguments."""
    result = CliRunner().invoke(
        trigger_module.webhook.commands["create"], ["webhook-trigger"]
    )

    assert result.exit_code != 0
    assert "Missing option '--webhook'" in result.output


def test_update_webhook_trigger_replaces_complete_config(
    monkeypatch, tmp_path: Path
) -> None:
    """Update passes the complete replacement configuration."""
    calls = []

    class _Client:
        def update_webhook_trigger(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(trigger_module, "Client", _Client)
    config_path = tmp_path / "replacement.yaml"
    config_path.write_text("target_events: []\n")

    result = CliRunner().invoke(
        trigger_module.webhook.commands["update"],
        ["custom-trigger", "--config", str(config_path)],
    )

    assert result.exit_code == 0, result.output
    assert calls[0]["configuration"].target_events == []
