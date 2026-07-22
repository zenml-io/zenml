#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
from types import SimpleNamespace
from unittest import mock
from uuid import uuid4

import pytest
import yaml

from zenml.enums import StackComponentType
from zenml.orchestrators.utils import (
    dump_compose_yaml,
    get_orchestrator_run_name,
    get_step_entrypoint_command,
    is_setting_enabled,
    register_artifact_store_filesystem,
)


def _compose_interpolate(yaml_text: str) -> str:
    """Mimic Docker Compose's literal-``$`` handling: ``$$`` collapses to ``$``.

    Compose interpolates ``$VAR``/``${VAR}`` against the environment and treats
    ``$$`` as an escaped literal ``$``. This models only the escape collapse,
    which is enough to prove that a serialized value round-trips verbatim.
    """
    return yaml_text.replace("$$", "$")


def test_dump_compose_yaml_escapes_dollar_signs():
    """Every ``$`` is escaped so Compose does not interpolate our values."""
    compose = {
        "services": {
            "step": {
                "environment": {
                    "DB_PASSWORD": "pa$$word",
                    "API_KEY": "abc$UNSET",
                    "HARDFAIL": "x${MISSING:?boom}y",
                },
                "volumes": ["/srv/$DATA:/data"],
            }
        }
    }

    dumped = dump_compose_yaml(compose)

    # No lone "$" survives: each original "$" became "$$".
    assert "$" in dumped
    assert "$" not in dumped.replace("$$", "")

    # After Compose collapses "$$" -> "$", the parsed values are byte-identical
    # to the originals: no interpolation, no truncation, no mangling.
    recovered = yaml.safe_load(_compose_interpolate(dumped))
    service = recovered["services"]["step"]
    assert service["environment"] == compose["services"]["step"]["environment"]
    assert service["volumes"] == compose["services"]["step"]["volumes"]


def test_dump_compose_yaml_no_dollar_is_unchanged_content():
    """A definition without ``$`` round-trips to identical parsed content."""
    compose = {"services": {"s": {"image": "img:latest", "environment": {}}}}
    assert yaml.safe_load(dump_compose_yaml(compose)) == compose


class _FakeEntrypointConfig:
    """Fake entrypoint configuration class for testing."""

    @classmethod
    def get_entrypoint_command(cls):
        return ["python", "-m", "zenml.entrypoint"]

    @classmethod
    def get_entrypoint_arguments(cls, step_name, snapshot_id, step_run_id):
        return ["--step", step_name]


def test_get_step_entrypoint_command_for_command_step():
    """Tests that the helper returns the custom command for a command step."""
    config = SimpleNamespace(command=["python", "train.py"])
    command, args = get_step_entrypoint_command(
        invocation_id="train",
        config=config,
        entrypoint_config_class=_FakeEntrypointConfig,
        snapshot_id=uuid4(),
        step_run_id=uuid4(),
    )
    assert command == ["python", "train.py"]
    assert args == []


def test_get_step_entrypoint_command_for_regular_step():
    """Tests that the helper returns the ZenML entrypoint for a regular step."""
    config = SimpleNamespace(command=None)
    command, args = get_step_entrypoint_command(
        invocation_id="train",
        config=config,
        entrypoint_config_class=_FakeEntrypointConfig,
        snapshot_id=uuid4(),
        step_run_id=uuid4(),
    )
    assert command == ["python", "-m", "zenml.entrypoint"]
    assert args == ["--step", "train"]


def test_is_setting_enabled():
    """Unit test for `is_setting_enabled()`.

    Tests that:
    - caching is enabled by default (when neither step nor pipeline set it),
    - caching is always enabled if explicitly enabled for the step,
    - caching is always disabled if explicitly disabled for the step,
    - caching is set to the pipeline cache if not configured for the step.
    """
    # Caching is enabled by default
    assert (
        is_setting_enabled(
            is_enabled_on_step=None, is_enabled_on_pipeline=None
        )
        is True
    )

    # Caching is always enabled if explicitly enabled for the step
    assert (
        is_setting_enabled(
            is_enabled_on_step=True,
            is_enabled_on_pipeline=True,
        )
        is True
    )

    assert (
        is_setting_enabled(
            is_enabled_on_step=True,
            is_enabled_on_pipeline=False,
        )
        is True
    )

    assert (
        is_setting_enabled(
            is_enabled_on_step=True,
            is_enabled_on_pipeline=None,
        )
        is True
    )

    # Caching is always disabled if explicitly disabled for the step
    assert (
        is_setting_enabled(
            is_enabled_on_step=False,
            is_enabled_on_pipeline=True,
        )
        is False
    )

    assert (
        is_setting_enabled(
            is_enabled_on_step=False,
            is_enabled_on_pipeline=False,
        )
        is False
    )

    assert (
        is_setting_enabled(
            is_enabled_on_step=False,
            is_enabled_on_pipeline=None,
        )
        is False
    )

    # Caching is set to the pipeline cache if not configured for the step
    assert (
        is_setting_enabled(
            is_enabled_on_step=None,
            is_enabled_on_pipeline=True,
        )
        is True
    )

    assert (
        is_setting_enabled(
            is_enabled_on_step=None,
            is_enabled_on_pipeline=False,
        )
        is False
    )


def test_register_artifact_store_filesystem(clean_client):
    """Tests if a new filesystem gets registered with the context manager."""
    with mock.patch(
        "zenml.artifact_stores.base_artifact_store.BaseArtifactStore._register"
    ) as register:
        # Calling the active artifact store will call register once
        _ = clean_client.active_stack.artifact_store
        assert register.call_count == 1

        new_artifact_store_model = clean_client.create_stack_component(
            name="new_local_artifact_store",
            flavor="local",
            component_type=StackComponentType.ARTIFACT_STORE,
            configuration={"path": ""},
        )
        with register_artifact_store_filesystem(new_artifact_store_model.id):
            # Entering the context manager will register the new filesystem
            assert register.call_count == 2

        # Exiting the context manager will set it back by calling register again
        assert register.call_count == 3


def test_get_orchestrator_run_name():
    """Tests the orchestrator run name computation."""
    pipeline_name = "pipeline"
    assert len(get_orchestrator_run_name(pipeline_name)) == 8 + 1 + 32
    assert len(get_orchestrator_run_name(pipeline_name, max_length=16)) == 16
    assert get_orchestrator_run_name(pipeline_name, max_length=16).startswith(
        pipeline_name
    )
    assert get_orchestrator_run_name(pipeline_name, max_length=17).startswith(
        f"{pipeline_name}_"
    )

    with pytest.raises(ValueError):
        get_orchestrator_run_name(pipeline_name, max_length=7)
