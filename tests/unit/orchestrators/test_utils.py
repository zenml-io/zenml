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
import random
from types import SimpleNamespace
from unittest import mock
from uuid import uuid4

import pytest
import yaml
from pydantic import ValidationError

from zenml.constants import (
    ENV_ZENML_USE_GLOBAL_RANDOM_SEED,
    UNRECOVERABLE_ORCHESTRATION_EXIT_CODE,
)
from zenml.enums import ExecutionStatus, StackComponentType
from zenml.orchestrators.utils import (
    dump_compose_yaml,
    exit_on_unrecoverable_error,
    get_config_environment_vars,
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
                    "LITERAL_DOLLAR": "cost$$100",
                    "UNSET_REFERENCE": "abc$UNSET",
                    "HARD_FAIL_REFERENCE": "x${MISSING:?boom}y",
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


@pytest.mark.parametrize(
    "env_value, names_repeat", [("false", False), ("true", True)]
)
def test_get_orchestrator_run_name_global_seed(
    monkeypatch: pytest.MonkeyPatch, env_value: str, names_repeat: bool
) -> None:
    """Tests that run names only repeat for a repeated seed when users opt in."""
    monkeypatch.setenv(ENV_ZENML_USE_GLOBAL_RANDOM_SEED, env_value)

    random.seed(42)
    first = get_orchestrator_run_name("pipeline")
    random.seed(42)
    second = get_orchestrator_run_name("pipeline")

    assert (first == second) is names_repeat


def test_get_config_environment_vars_forwards_global_seed_setting(
    clean_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tests that the global seed setting reaches the run environment."""
    monkeypatch.delenv(ENV_ZENML_USE_GLOBAL_RANDOM_SEED, raising=False)
    environment, _ = get_config_environment_vars()
    assert ENV_ZENML_USE_GLOBAL_RANDOM_SEED not in environment

    monkeypatch.setenv(ENV_ZENML_USE_GLOBAL_RANDOM_SEED, "true")
    environment, _ = get_config_environment_vars()
    assert environment[ENV_ZENML_USE_GLOBAL_RANDOM_SEED] == "true"


@pytest.fixture
def run_store():
    """Patches the store calls that fail a pipeline run."""
    with (
        mock.patch("zenml.orchestrators.utils.Client") as client,
        mock.patch(
            "zenml.orchestrators.utils.publish_failed_pipeline_run"
        ) as publish_failed,
    ):
        yield SimpleNamespace(
            get_run=client.return_value.zen_store.get_run,
            publish_failed=publish_failed,
        )


def test_exit_on_unrecoverable_error_ignores_recoverable_errors(run_store):
    """Tests that errors a retry might fix leave the run alone."""
    exit_on_unrecoverable_error(
        RuntimeError("Server unavailable"), run_id=uuid4()
    )

    run_store.get_run.assert_not_called()
    run_store.publish_failed.assert_not_called()


@pytest.mark.parametrize(
    "exception",
    [
        ValidationError.from_exception_data("StackResponse", []),
        ModuleNotFoundError("No module named 'sklearn'"),
    ],
)
@pytest.mark.parametrize(
    "status",
    [
        ExecutionStatus.INITIALIZING,
        ExecutionStatus.PROVISIONING,
        ExecutionStatus.RUNNING,
        ExecutionStatus.RESUMING,
    ],
)
def test_exit_on_unrecoverable_error_fails_unfinished_run(
    run_store, exception, status
):
    """Tests that an unrecoverable error fails a run that nothing else ends."""
    run_id = uuid4()
    run_store.get_run.return_value = SimpleNamespace(status=status)

    with pytest.raises(SystemExit) as exc_info:
        exit_on_unrecoverable_error(exception, run_id=run_id)

    assert exc_info.value.code == UNRECOVERABLE_ORCHESTRATION_EXIT_CODE
    run_store.publish_failed.assert_called_once()
    assert run_store.publish_failed.call_args.args == (run_id,)
    exception_info = run_store.publish_failed.call_args.kwargs[
        "exception_info"
    ]
    assert type(exception).__name__ in exception_info.traceback


@pytest.mark.parametrize(
    "status",
    [
        ExecutionStatus.STOPPING,
        ExecutionStatus.STOPPED,
        ExecutionStatus.COMPLETED,
        ExecutionStatus.FAILED,
    ],
)
def test_exit_on_unrecoverable_error_keeps_stopping_and_finished_runs(
    run_store, status
):
    """Tests that a stop request or a final status takes precedence."""
    run_store.get_run.return_value = SimpleNamespace(status=status)

    with pytest.raises(SystemExit):
        exit_on_unrecoverable_error(ImportError(), run_id=uuid4())

    run_store.publish_failed.assert_not_called()


def test_exit_on_unrecoverable_error_without_reachable_run(run_store):
    """Tests that an unknown or unreachable run doesn't prevent the exit."""
    with pytest.raises(SystemExit):
        exit_on_unrecoverable_error(ImportError(), run_id=None)
    run_store.get_run.assert_not_called()

    run_store.get_run.side_effect = ConnectionError("Server unavailable")
    with pytest.raises(SystemExit):
        exit_on_unrecoverable_error(ImportError(), run_id=uuid4())
    run_store.publish_failed.assert_not_called()
