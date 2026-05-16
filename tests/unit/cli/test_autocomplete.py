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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Tests for ZenML CLI shell completion."""

import os
import subprocess
import sys
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest
from click.testing import CliRunner

from zenml.cli import completion
from zenml.cli.cli import cli
from zenml.enums import StackComponentType


def _complete(words: str, cword: int) -> str:
    """Run Bash completion against the root CLI."""
    result = CliRunner().invoke(
        cli,
        [],
        prog_name="zenml",
        env={
            "_ZENML_COMPLETE": "bash_complete",
            "COMP_WORDS": words,
            "COMP_CWORD": str(cword),
        },
    )
    assert result.exit_code == 0
    return result.output


def test_root_command_completion_includes_stack() -> None:
    """Custom root CLI group remains compatible with Click completion."""
    output = _complete("zenml st", 1)

    assert "plain,stack" in output
    assert "plain,status" in output


def test_nested_stack_command_completion_includes_set() -> None:
    """TagGroup command completion works for nested command groups."""
    output = _complete("zenml stack s", 2)

    assert "plain,set" in output


def test_entrypoint_completion_script_uses_stdout() -> None:
    """The installed entrypoint path preserves stdout for Click completion."""
    env = os.environ.copy()
    env["_ZENML_COMPLETE"] = "bash_source"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import zenml_cli; zenml_cli.cli(prog_name='zenml')",
        ],
        cwd=os.getcwd(),
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "_ZENML_COMPLETE" in result.stdout
    assert "_ZENML_COMPLETE" not in result.stderr


def test_dynamic_stack_completion_filters_sorts_and_deduplicates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dynamic completions return bounded name candidates."""
    calls: List[Dict[str, Any]] = []

    class MockClient:
        def list_stacks(self, **kwargs: Any) -> List[SimpleNamespace]:
            calls.append(kwargs)
            return [
                SimpleNamespace(name="beta"),
                SimpleNamespace(name="alpha"),
                SimpleNamespace(name="alpha"),
                SimpleNamespace(name="other"),
            ]

    monkeypatch.setattr(completion, "Client", MockClient)

    assert completion.complete_stack_names(None, None, "a") == ["alpha"]  # type: ignore[arg-type]
    assert calls == [{"name": "startswith:a", "size": 100, "hydrate": False}]


def test_dynamic_component_completion_is_type_scoped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Component completion passes the generator component type."""
    calls: List[Dict[str, Any]] = []

    class MockClient:
        def list_stack_components(
            self, **kwargs: Any
        ) -> List[SimpleNamespace]:
            calls.append(kwargs)
            return [SimpleNamespace(name="orch")]

    monkeypatch.setattr(completion, "Client", MockClient)

    callback = completion.complete_stack_component_names(
        StackComponentType.ORCHESTRATOR
    )
    assert callback(None, None, "o") == ["orch"]  # type: ignore[arg-type]
    assert calls == [
        {
            "type": StackComponentType.ORCHESTRATOR,
            "name": "startswith:o",
            "size": 100,
            "hydrate": False,
        }
    ]


def test_dynamic_secret_completion_is_silent_and_fail_closed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Completion suppresses stdout and returns no candidates on failures."""

    class NoisyFailingClient:
        def list_secrets(self, **kwargs: Any) -> List[SimpleNamespace]:
            print("this must not corrupt completion")
            raise NotImplementedError("secrets disabled")

    monkeypatch.setattr(completion, "Client", NoisyFailingClient)

    assert completion.complete_secret_names(None, None, "s") == []  # type: ignore[arg-type]
    captured = capsys.readouterr()
    assert "this must not corrupt completion" not in captured.out


def test_connector_metadata_completion_uses_list_types(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Connector metadata completion does not enumerate remote resources."""
    calls: List[Dict[str, Any]] = []
    connector_type = SimpleNamespace(
        connector_type="aws",
        resource_types=[
            SimpleNamespace(resource_type="s3-bucket"),
            SimpleNamespace(resource_type="eks-cluster"),
        ],
        auth_method_dict={"iam-role": object(), "secret-key": object()},
    )

    class MockClient:
        def list_service_connector_types(
            self, **kwargs: Any
        ) -> List[SimpleNamespace]:
            calls.append(kwargs)
            return [connector_type]

    monkeypatch.setattr(completion, "Client", MockClient)
    ctx = SimpleNamespace(params={"connector_type": "aws"})

    assert completion.complete_service_connector_types(None, None, "a") == [  # type: ignore[arg-type]
        "aws"
    ]
    assert completion.complete_service_connector_resource_types(  # type: ignore[arg-type]
        ctx, None, "s"
    ) == ["s3-bucket"]
    assert completion.complete_service_connector_auth_methods(  # type: ignore[arg-type]
        ctx, None, "i"
    ) == ["iam-role"]
    assert calls == [{}, {"connector_type": "aws"}, {"connector_type": "aws"}]
