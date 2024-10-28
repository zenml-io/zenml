#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
import os
from contextlib import ExitStack as does_not_raise
from unittest.mock import ANY, patch
from uuid import uuid4

import pytest

from tests.unit.conftest_new import empty_pipeline  # noqa
from zenml.client import Client
from zenml.config.compiler import Compiler
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.enums import ExecutionStatus
from zenml.exceptions import (
    StackValidationError,
)
from zenml.models import (
    Page,
    PipelineBuildBase,
)
from zenml.pipelines import Schedule, pipeline
from zenml.steps import step


def test_calling_a_pipeline_twice_raises_no_exception(
    one_step_pipeline, empty_step
):
    """Tests that calling one pipeline instance twice does not raise any exception."""
    pipeline_instance = one_step_pipeline(empty_step)

    with does_not_raise():
        pipeline_instance.with_options(unlisted=True)()
        pipeline_instance.with_options(unlisted=True)()


@step
def step_with_output() -> int:
    return 1


@step
def step_with_three_inputs(a: int, b: int, c: int) -> None:
    pass


def test_step_can_receive_the_same_input_artifact_multiple_times():
    """Tests that a step can receive the same input artifact multiple times."""

    @pipeline
    def test_pipeline():
        output = step_with_output()
        step_with_three_inputs(a=output, b=output, c=output)

    with does_not_raise():
        test_pipeline.with_options(unlisted=True)()


@step(step_operator="azureml")
def step_that_requires_step_operator() -> None:
    pass


def test_pipeline_run_fails_when_required_step_operator_is_missing(
    one_step_pipeline,
):
    """Tests that running a pipeline with a step that requires a custom step
    operator fails if the active stack does not contain this step operator."""
    assert not Client().active_stack.step_operator
    with pytest.raises(StackValidationError):
        one_step_pipeline(step_that_requires_step_operator).with_options(
            unlisted=True
        )()


def test_pipeline_decorator_configuration_gets_applied_during_initialization(
    mocker,
):
    """Tests that the configuration passed to the pipeline decorator gets
    applied when creating an instance of the pipeline."""
    config = {
        "name": "pipeline_name",
        "extra": {"key": "value"},
    }

    @pipeline(**config)
    def pipeline_instance():
        pass

    assert pipeline_instance.configuration.name == "pipeline_name"
    assert pipeline_instance.configuration.extra == {"key": "value"}


def test_pipeline_configuration(empty_pipeline):  # noqa: F811
    """Tests the pipeline configuration and overwriting/merging with existing
    configurations."""
    pipeline_instance = empty_pipeline

    pipeline_instance.configure(
        enable_cache=False,
        extra={"key": "value"},
    )

    assert pipeline_instance.configuration.enable_cache is False
    assert pipeline_instance.configuration.extra == {"key": "value"}

    # No merging
    pipeline_instance.configure(
        enable_cache=True,
        extra={"key2": "value2"},
        merge=False,
    )
    assert pipeline_instance.configuration.enable_cache is True
    assert pipeline_instance.configuration.extra == {"key2": "value2"}

    # With merging
    pipeline_instance.configure(
        enable_cache=False,
        extra={"key3": "value3"},
        merge=True,
    )
    assert pipeline_instance.configuration.enable_cache is False
    assert pipeline_instance.configuration.extra == {
        "key2": "value2",
        "key3": "value3",
    }


def test_configure_pipeline_with_invalid_settings_key(
    empty_pipeline,  # noqa: F811
):
    """Tests that configuring a pipeline with an invalid settings key raises an
    error."""
    with pytest.raises(ValueError):
        empty_pipeline.configure(settings={"invalid_settings_key": {}})


def test_run_configuration_in_code(
    mocker, clean_client: "Client", one_step_pipeline, empty_step
):
    """Tests configuring a pipeline run in code."""
    mock_compile = mocker.patch.object(
        Compiler, "compile", wraps=Compiler().compile
    )
    pipeline_instance = one_step_pipeline(empty_step)

    schedule = Schedule(cron_expression="5 * * * *")

    with patch(
        "zenml.orchestrators.base_orchestrator.BaseOrchestratorConfig.is_schedulable",
        new_callable=lambda: True,
    ):
        pipeline_instance.with_options(
            run_name="run_name", schedule=schedule
        )()

    expected_run_config = PipelineRunConfiguration(
        run_name="run_name", schedule=schedule
    )
    mock_compile.assert_called_once_with(
        pipeline=ANY, stack=ANY, run_configuration=expected_run_config
    )


def test_run_configuration_from_file(
    mocker, clean_client: "Client", one_step_pipeline, empty_step, tmp_path
):
    """Tests configuring a pipeline run from a file."""
    mock_compile = mocker.patch.object(
        Compiler, "compile", wraps=Compiler().compile
    )
    pipeline_instance = one_step_pipeline(empty_step)

    schedule = Schedule(cron_expression="5 * * * *")

    config_path = tmp_path / "config.yaml"
    expected_run_config = PipelineRunConfiguration(
        run_name="run_name", schedule=schedule
    )
    config_path.write_text(expected_run_config.yaml())

    with patch(
        "zenml.orchestrators.base_orchestrator.BaseOrchestratorConfig.is_schedulable",
        new_callable=lambda: True,
    ):
        pipeline_instance.with_options(config_path=str(config_path))()
    mock_compile.assert_called_once_with(
        pipeline=ANY, stack=ANY, run_configuration=expected_run_config
    )


def test_run_configuration_from_code_and_file(
    mocker, clean_client: "Client", one_step_pipeline, empty_step, tmp_path
):
    """Tests merging the configuration of a pipeline run from a file and within
    code."""
    mock_compile = mocker.patch.object(
        Compiler, "compile", wraps=Compiler().compile
    )
    pipeline_instance = one_step_pipeline(empty_step)

    schedule = Schedule(cron_expression="5 * * * *")

    config_path = tmp_path / "config.yaml"
    file_config = PipelineRunConfiguration(
        run_name="run_name_in_file", schedule=schedule
    )
    config_path.write_text(file_config.yaml())

    with patch(
        "zenml.orchestrators.base_orchestrator.BaseOrchestratorConfig.is_schedulable",
        new_callable=lambda: True,
    ):
        pipeline_instance.with_options(
            config_path=str(config_path),
            run_name="run_name_in_code",
        )()

    expected_run_config = PipelineRunConfiguration(
        run_name="run_name_in_code",
        schedule=Schedule(cron_expression="5 * * * *"),
    )
    mock_compile.assert_called_once_with(
        pipeline=ANY, stack=ANY, run_configuration=expected_run_config
    )


def test_pipeline_configuration_with_steps_argument(
    mocker, clean_client: "Client", one_step_pipeline, empty_step
):
    """Tests that the `with_options` method allows configuring step configs with
    the `steps` argument."""
    mock_compile = mocker.patch.object(
        Compiler, "compile", wraps=Compiler().compile
    )
    pipeline_instance = one_step_pipeline(empty_step)

    step_configs = {"_empty_step": {"enable_artifact_visualization": False}}
    pipeline_instance.with_options(steps=step_configs)()

    expected_run_config = PipelineRunConfiguration(steps=step_configs)
    mock_compile.assert_called_once_with(
        pipeline=ANY, stack=ANY, run_configuration=expected_run_config
    )


def test_pipeline_configuration_with_duplicate_step_configurations(
    mocker, clean_client: "Client", one_step_pipeline, empty_step
):
    """Tests that the `with_options` method ignores the `steps` argument if a
    value is also passed using the `step_configurations` argument."""

    mock_compile = mocker.patch.object(
        Compiler, "compile", wraps=Compiler().compile
    )
    pipeline_instance = one_step_pipeline(empty_step)

    step_configs = {"_empty_step": {"enable_artifact_visualization": False}}
    ignored_step_configs = {"_empty_step": {"enable_artifact_metadata": False}}

    pipeline_instance.with_options(
        step_configurations=step_configs, steps=ignored_step_configs
    )()

    expected_run_config = PipelineRunConfiguration(steps=step_configs)
    mock_compile.assert_called_once_with(
        pipeline=ANY, stack=ANY, run_configuration=expected_run_config
    )


@step(enable_cache=True)
def step_with_cache_enabled() -> None:
    pass


@step(enable_cache=False)
def step_with_cache_disabled() -> None:
    pass


@pipeline(enable_cache=True)
def pipeline_with_cache_enabled() -> None:
    step_with_cache_enabled()
    step_with_cache_disabled()


@pipeline(enable_cache=False)
def pipeline_with_cache_disabled() -> None:
    step_with_cache_enabled()
    step_with_cache_disabled()


# TODO: This never worked for the new pipeline class, figure out a way to
# reenable this once we figured out the config precedence
# def test_setting_enable_cache_at_run_level_overrides_all_decorator_values(
#     mocker: MockFixture,
# ):
#     """Test that `pipeline.with_options(enable_cache=...)` overrides decorator values."""

#     def assert_cache_enabled(
#         deployment: PipelineDeploymentBase,
#         placeholder_run: Optional[PipelineRunResponse] = None,
#     ):
#         assert deployment.pipeline_configuration.enable_cache is True
#         for step_ in deployment.step_configurations.values():
#             assert step_.config.enable_cache is True

#     def assert_cache_disabled(
#         deployment: PipelineDeploymentBase,
#         placeholder_run: Optional[PipelineRunResponse] = None,
#     ):
#         assert deployment.pipeline_configuration.enable_cache is False
#         for step_ in deployment.step_configurations.values():
#             assert step_.config.enable_cache is False

#     cache_enabled_mock = mocker.MagicMock(side_effect=assert_cache_enabled)
#     cache_disabled_mock = mocker.MagicMock(side_effect=assert_cache_disabled)

#     # Test that `enable_cache=True` overrides all decorator values
#     mocker.patch(
#         "zenml.stack.stack.Stack.deploy_pipeline", new=cache_enabled_mock
#     )
#     pipeline_with_cache_disabled.with_options(
#         unlisted=True, enable_cache=True
#     )()
#     assert cache_enabled_mock.call_count == 1

#     # Test that `enable_cache=False` overrides all decorator values
#     mocker.patch(
#         "zenml.stack.stack.Stack.deploy_pipeline", new=cache_disabled_mock
#     )
#     pipeline_with_cache_enabled.with_options(
#         unlisted=True, enable_cache=False
#     )()
#     assert cache_disabled_mock.call_count == 1


def test_unique_identifier_considers_spec(empty_step):
    """Tests that the unique pipeline ID depends on the pipeline spec."""

    @pipeline
    def pipeline_instance():
        empty_step(id="step_1")
        empty_step(id="step_2", after="step_1")

    pipeline_instance.prepare()
    spec = Compiler().compile_spec(pipeline=pipeline_instance)
    id_ = pipeline_instance._compute_unique_identifier(spec)

    @pipeline
    def new_instance():
        empty_step(id="step_1")
        step_with_cache_enabled(id="step_2", after="step_1")

    new_instance.prepare()
    new_spec = Compiler().compile_spec(pipeline=new_instance)
    new_id = new_instance._compute_unique_identifier(new_spec)

    assert spec != new_spec
    assert id_ != new_id


def test_unique_identifier_considers_step_source_code(
    one_step_pipeline, empty_step, mocker
):
    """Tests that the unique pipeline ID depends on the step source code."""
    pipeline_instance = one_step_pipeline(empty_step)

    pipeline_instance.prepare()
    spec = Compiler().compile_spec(pipeline=pipeline_instance)
    id_ = pipeline_instance._compute_unique_identifier(spec)

    # Change step source -> new ID
    mocker.patch(
        "zenml.steps.base_step.BaseStep.source_code",
        new_callable=mocker.PropertyMock,
        return_value="step_source_code",
    )

    new_id = pipeline_instance._compute_unique_identifier(spec)
    assert id_ != new_id


def test_reusing_pipeline(
    mocker,
    empty_pipeline,  # noqa: F811
    create_pipeline_model,
):
    """Tests reusing an already registered pipeline version."""
    pipeline_model = create_pipeline_model(version="3")
    mocker.patch(
        "zenml.client.Client.list_pipelines",
        return_value=Page(
            index=1,
            max_size=1,
            total_pages=1,
            total=1,
            items=[pipeline_model],
        ),
    )

    pipeline_instance = empty_pipeline
    result = pipeline_instance.register()

    assert result == pipeline_model


def test_compiling_a_pipeline_merges_schedule(
    empty_pipeline,  # noqa: F811
    tmp_path,
):
    """Tests that compiling a pipeline merges the schedule from the config
    file and in-code configuration."""
    config_path = tmp_path / "config.yaml"
    run_config = PipelineRunConfiguration(
        schedule=Schedule(name="schedule_name", cron_expression="* * * * *")
    )
    config_path.write_text(run_config.yaml())

    pipeline_instance = empty_pipeline
    with pipeline_instance:
        pipeline_instance.entrypoint()

    _, schedule, _ = pipeline_instance._compile(
        config_path=str(config_path),
        schedule=Schedule(cron_expression="5 * * * *", catchup=True),
    )

    assert schedule.name == "schedule_name"
    assert schedule.cron_expression == "5 * * * *"
    assert schedule.catchup is True


def test_compiling_a_pipeline_merges_build(
    empty_pipeline,  # noqa: F811
    tmp_path,
):
    """Tests that compiling a pipeline merges the build/build ID from the config
    file and in-code configuration."""
    config_path_with_build_id = tmp_path / "config.yaml"
    config_path_with_build = tmp_path / "config2.yaml"

    run_config_with_build_id = PipelineRunConfiguration(build=uuid4())
    config_path_with_build_id.write_text(run_config_with_build_id.yaml())

    run_config_with_build = PipelineRunConfiguration(
        build=PipelineBuildBase(is_local=True, contains_code=True)
    )
    config_path_with_build.write_text(run_config_with_build.yaml())

    in_code_build_id = uuid4()

    pipeline_instance = empty_pipeline
    with pipeline_instance:
        pipeline_instance.entrypoint()

    # Config with ID
    _, _, build = pipeline_instance._compile(
        config_path=str(config_path_with_build_id), build=in_code_build_id
    )
    assert build == in_code_build_id
    # Config with build object
    _, _, build = pipeline_instance._compile(
        config_path=str(config_path_with_build), build=in_code_build_id
    )
    assert build == in_code_build_id

    in_code_build = PipelineBuildBase(
        images={"key": {"image": "image_name"}},
        is_local=False,
        contains_code=True,
    )
    # Config with ID
    _, _, build = pipeline_instance._compile(
        config_path=str(config_path_with_build_id), build=in_code_build
    )
    assert build == in_code_build
    # Config with build object
    _, _, build = pipeline_instance._compile(
        config_path=str(config_path_with_build), build=in_code_build
    )
    assert build == in_code_build


def test_building_a_pipeline_registers_it(
    clean_client,
    empty_pipeline,  # noqa: F811
):
    """Tests that building a pipeline registers it in the server."""
    pipeline_instance = empty_pipeline
    with pytest.raises(KeyError):
        clean_client.get_pipeline(name_id_or_prefix=pipeline_instance.name)

    pipeline_instance.build()
    assert (
        clean_client.get_pipeline(name_id_or_prefix=pipeline_instance.name)
        is not None
    )


def is_placeholder_request(run_request) -> bool:
    """Checks whether a pipeline run request refers to a placeholder run."""
    return (
        run_request.status == ExecutionStatus.INITIALIZING
        and run_request.orchestrator_environment == {}
        and run_request.orchestrator_run_id is None
    )


def test_running_pipeline_creates_and_uses_placeholder_run(
    mocker,
    clean_client,
    empty_pipeline,  # noqa: F811
):
    """Tests that running a pipeline creates a placeholder run and later
    replaces it with the actual run."""
    mock_create_run = mocker.patch.object(
        type(clean_client.zen_store),
        "create_run",
        wraps=clean_client.zen_store.create_run,
    )
    mock_get_or_create_run = mocker.patch.object(
        type(clean_client.zen_store),
        "get_or_create_run",
        wraps=clean_client.zen_store.get_or_create_run,
    )

    pipeline_instance = empty_pipeline
    assert clean_client.list_pipeline_runs().total == 0

    pipeline_instance()

    mock_create_run.assert_called_once()
    mock_get_or_create_run.assert_called_once()

    placeholder_run_request = mock_create_run.call_args[0][0]  # First arg
    assert is_placeholder_request(placeholder_run_request)

    replace_request = mock_get_or_create_run.call_args[0][0]  # First arg
    assert not is_placeholder_request(replace_request)

    runs = clean_client.list_pipeline_runs()
    assert runs.total == 1

    run = runs[0]
    assert run.status == ExecutionStatus.COMPLETED
    assert (
        run.orchestrator_environment
        == replace_request.orchestrator_environment
    )
    assert run.orchestrator_run_id == replace_request.orchestrator_run_id
    # assert run.deployment_id


def test_rerunning_deloyment_does_not_fail(
    mocker,
    clean_client,
    empty_pipeline,  # noqa: F811
):
    """Tests that a deployment can be re-run without issues."""
    mock_create_run = mocker.patch.object(
        type(clean_client.zen_store),
        "create_run",
        wraps=clean_client.zen_store.create_run,
    )
    mock_get_or_create_run = mocker.patch.object(
        type(clean_client.zen_store),
        "get_or_create_run",
        wraps=clean_client.zen_store.get_or_create_run,
    )

    pipeline_instance = empty_pipeline
    pipeline_instance()

    deployments = clean_client.list_deployments()
    assert deployments.total == 1
    deployment = deployments[0]

    stack = clean_client.active_stack

    # Simulate re-running the deployment
    stack.deploy_pipeline(deployment)

    assert mock_create_run.call_count == 2
    assert mock_get_or_create_run.call_count == 2

    placeholder_request = mock_create_run.call_args_list[0][0][0]
    assert is_placeholder_request(placeholder_request)

    run_request = mock_create_run.call_args_list[1][0][0]
    assert not is_placeholder_request(run_request)

    runs = clean_client.list_pipeline_runs(deployment_id=deployment.id)
    assert runs.total == 2


def test_failure_during_initialization_deletes_placeholder_run(
    clean_client,
    empty_pipeline,  # noqa: F811
    mocker,
):
    """Tests that when a pipeline run fails during initialization, the
    placeholder run that was created for it is deleted."""
    mock_create_run = mocker.patch.object(
        type(clean_client.zen_store),
        "create_run",
        wraps=clean_client.zen_store.create_run,
    )
    mock_delete_run = mocker.patch.object(
        type(clean_client.zen_store),
        "delete_run",
        wraps=clean_client.zen_store.delete_run,
    )

    pipeline_instance = empty_pipeline
    assert clean_client.list_pipeline_runs().total == 0

    mocker.patch(
        "zenml.stack.stack.Stack.deploy_pipeline", side_effect=RuntimeError
    )

    with pytest.raises(RuntimeError):
        pipeline_instance()

    mock_create_run.assert_called_once()
    mock_delete_run.assert_called_once()

    assert clean_client.list_pipeline_runs().total == 0


def test_running_scheduled_pipeline_does_not_create_placeholder_run(
    mocker,
    clean_client: "Client",
    empty_pipeline,  # noqa: F811
):
    """Tests that running a scheduled pipeline does not create a placeholder run
    in the database."""
    mock_create_run = mocker.patch.object(
        type(clean_client.zen_store),
        "create_run",
        wraps=clean_client.zen_store.create_run,
    )
    pipeline_instance = empty_pipeline

    with patch(
        "zenml.orchestrators.base_orchestrator.BaseOrchestratorConfig.is_schedulable",
        new_callable=lambda: True,
    ):
        scheduled_pipeline_instance = pipeline_instance.with_options(
            schedule=Schedule(cron_expression="*/5 * * * *")
        )
        scheduled_pipeline_instance()

    mock_create_run.assert_called_once()
    run_request = mock_create_run.call_args[0][0]  # First arg
    assert not is_placeholder_request(run_request)


def test_env_var_substitution(clean_client, empty_pipeline):  # noqa: F811
    """Test env var substitution in pipeline config."""
    with patch.dict(os.environ, {"A": "1"}):
        empty_pipeline.configure(extra={"key": "${A}_suffix"})
        run = empty_pipeline()

        assert run.config.extra["key"] == "1_suffix"


def test_run_tagging(clean_client, tmp_path, empty_pipeline):  # noqa: F811
    """Test run tagging."""

    config_path = tmp_path / "config.yaml"
    config_path.write_text("tags: [tag_3]")

    empty_pipeline.configure(tags=["tag_1"])
    p = empty_pipeline.with_options(
        tags=["tag_2"], config_path=str(config_path)
    )
    run = p()

    assert {tag.name for tag in run.tags} == {"tag_1", "tag_2", "tag_3"}
