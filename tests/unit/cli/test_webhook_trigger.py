#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Tests for webhook trigger CLI configuration."""

from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from click.testing import CliRunner

from zenml.enums import WebhookType
from zenml.models import MergedPullRequest, PushEvent

trigger_module = import_module("zenml.cli.trigger")


def test_webhook_trigger_help_describes_event_config_formats() -> None:
    """Create and update help expose provider-specific YAML guidance."""
    create_result = CliRunner().invoke(
        trigger_module.webhook.commands["create"], ["--help"]
    )
    update_result = CliRunner().invoke(
        trigger_module.webhook.commands["update"], ["--help"]
    )

    assert create_result.exit_code == 0, create_result.output
    assert update_result.exit_code == 0, update_result.output
    for output in [create_result.output, update_result.output]:
        assert "type: merged_pull_request" in output
        assert "type: workflow_run_completed" in output
        assert "type: push" in output
        assert "type: release_published" in output
        assert "Custom webhook triggers" in output
        assert "<OWNER>/<REPOSITORY>" in output
        assert "<GITHUB_LOGIN>" in output

    assert "--event-config is required" in create_result.output
    assert "atomically replaces the entire" in update_result.output
    assert "omitting it preserves" in update_result.output


def test_create_github_webhook_trigger_loads_event_config(
    monkeypatch, tmp_path: Path
) -> None:
    """GitHub event YAML produces the public typed event models."""
    calls = []

    class _Client:
        def create_webhook_trigger(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(id=uuid4())

    monkeypatch.setattr(trigger_module, "Client", _Client)
    command = trigger_module.webhook.commands["create"]
    config_path = tmp_path / "events.yaml"
    config_path.write_text(
        """
events:
  - type: merged_pull_request
    repo: zenml-io/zenml
    target_branch: develop
    source_branch: startswith:feature/
    author: george
  - type: push
    repo: zenml-io/zenml
    branch: main
""".lstrip()
    )

    result = CliRunner().invoke(
        command,
        [
            "github-trigger",
            "--webhook-type",
            WebhookType.GITHUB.value,
            "--event-config",
            str(config_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls[0]["events"] == [
        MergedPullRequest(
            repo="zenml-io/zenml",
            target_branch="develop",
            source_branch="startswith:feature/",
            author="george",
        ),
        PushEvent(repo="zenml-io/zenml", branch="main"),
    ]


def test_create_github_webhook_trigger_requires_event_config(
    monkeypatch,
) -> None:
    """GitHub trigger creation rejects missing event configuration."""

    class _Client:
        pass

    monkeypatch.setattr(trigger_module, "Client", _Client)
    command = trigger_module.webhook.commands["create"]

    result = CliRunner().invoke(
        command,
        [
            "github-trigger",
            "--webhook-type",
            WebhookType.GITHUB.value,
        ],
    )

    assert result.exit_code != 0
    assert "require --event-config" in result.output


def test_update_webhook_trigger_replaces_events_from_config(
    monkeypatch, tmp_path: Path
) -> None:
    """The update command passes the complete replacement event list."""
    calls = []

    class _Client:
        def update_webhook_trigger(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(trigger_module, "Client", _Client)
    command = trigger_module.webhook.commands["update"]
    config_path = tmp_path / "replacement.yaml"
    config_path.write_text(
        """
events:
  - type: push
    repo: zenml-io/zenml
    branch: develop
  - type: push
    repo: zenml-io/zenml
    branch: main
""".lstrip()
    )

    result = CliRunner().invoke(
        command,
        ["github-trigger", "--event-config", str(config_path)],
    )

    assert result.exit_code == 0, result.output
    assert calls[0]["events"] == [
        PushEvent(repo="zenml-io/zenml", branch="develop"),
        PushEvent(repo="zenml-io/zenml", branch="main"),
    ]
