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
from contextlib import ExitStack as does_not_raise
from unittest.mock import ANY
from uuid import uuid4

import pytest
from pytest_mock import MockFixture

from tests.unit.conftest_new import empty_pipeline  # noqa
from zenml.client import Client
from zenml.config.compiler import Compiler
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.config.pipeline_spec import PipelineSpec
from zenml.enums import ExecutionStatus
from zenml.exceptions import (
    PipelineInterfaceError,
    StackValidationError,
)
from zenml.models import Page, PipelineBuildBase, PipelineDeploymentBase
from zenml.new.pipelines.pipeline import Pipeline
from zenml.pipelines import BasePipeline, Schedule, pipeline
from zenml.steps import BaseParameters, step


def create_pipeline_with_param_value(param_value: int):
    """Creates pipeline instance with a step named 'step' which has a parameter named 'value'."""

    class Params(BaseParameters):
        value: int

    @step
    def step_with_params(params: Params) -> None:
        pass

    @pipeline
    def some_pipeline(step_):
        step_()

    pipeline_instance = some_pipeline(
        step_=step_with_params(params=Params(value=param_value))
    )
    return pipeline_instance


def test_initialize_pipeline_with_args(
    unconnected_two_step_pipeline, generate_empty_steps
):
    """Test that a pipeline can be initialized with args."""
    with does_not_raise():
        empty_step_1, empty_step_2 = generate_empty_steps(2)
        unconnected_two_step_pipeline(empty_step_1(), empty_step_2())


def test_initialize_pipeline_with_kwargs(
    unconnected_two_step_pipeline, generate_empty_steps
):
    """Test that a pipeline can be initialized with kwargs."""
    with does_not_raise():
        empty_step_1, empty_step_2 = generate_empty_steps(2)
        unconnected_two_step_pipeline(
            step_1=empty_step_1(), step_2=empty_step_2()
        )


def test_initialize_pipeline_with_args_and_kwargs(
    unconnected_two_step_pipeline, generate_empty_steps
):
    """Test that a pipeline can be initialized with a mix of args and kwargs."""
    with does_not_raise():
        empty_step_1, empty_step_2 = generate_empty_steps(2)
        unconnected_two_step_pipeline(empty_step_1(), step_2=empty_step_2())


def test_initialize_pipeline_with_too_many_args(
    unconnected_two_step_pipeline, generate_empty_steps
):
    """Test that pipeline initialization fails when too many args are passed."""
    with pytest.raises(PipelineInterfaceError):
        empty_step_1, empty_step_2, empty_step_3 = generate_empty_steps(3)
        unconnected_two_step_pipeline(
            empty_step_1(), empty_step_2(), empty_step_3()
        )


def test_initialize_pipeline_with_too_many_args_and_kwargs(
    unconnected_two_step_pipeline, generate_empty_steps
):
    """Test that pipeline initialization fails when too many args and kwargs are passed."""
    with pytest.raises(PipelineInterfaceError):
        empty_step_1, empty_step_2, empty_step_3 = generate_empty_steps(3)
        unconnected_two_step_pipeline(
            empty_step_3(), step_1=empty_step_1(), step_2=empty_step_2()
        )


def test_initialize_pipeline_with_missing_key(
    unconnected_two_step_pipeline, empty_step
):
    """Test that pipeline initialization fails when an argument is missing."""
    with pytest.raises(PipelineInterfaceError):
        unconnected_two_step_pipeline(step_1=empty_step())


def test_initialize_pipeline_with_unexpected_key(
    unconnected_two_step_pipeline, generate_empty_steps
):
    """Test that pipeline initialization fails when an argument has an unexpected key."""
    with pytest.raises(PipelineInterfaceError):
        empty_step_1, empty_step_2, empty_step_3 = generate_empty_steps(3)
        unconnected_two_step_pipeline(
            step_1=empty_step_1(), step_2=empty_step_2(), step_3=empty_step_3()
        )


def test_initialize_pipeline_with_repeated_args(
    unconnected_two_step_pipeline, empty_step
):
    """Test that pipeline initialization works when same step object is used."""
    step_instance = empty_step()
    with does_not_raise():
        unconnected_two_step_pipeline(step_instance, step_instance)


def test_initialize_pipeline_with_repeated_kwargs(
    unconnected_two_step_pipeline, empty_step
):
    """Test that pipeline initialization works when same step object is used."""
    step_instance = empty_step()
    with does_not_raise():
        unconnected_two_step_pipeline(
            step_1=step_instance, step_2=step_instance
        )


def test_initialize_pipeline_with_repeated_args_and_kwargs(
    unconnected_two_step_pipeline, empty_step
):
    """Test that pipeline initialization works when same step object is used."""
    step_instance = empty_step()
    with does_not_raise():
        unconnected_two_step_pipeline(step_instance, step_2=step_instance)


def test_initialize_pipeline_with_wrong_arg_type(
    unconnected_two_step_pipeline, empty_step
):
    """Test that pipeline initialization fails when an arg has a wrong type."""
    with pytest.raises(PipelineInterfaceError):
        unconnected_two_step_pipeline(1, empty_step())


def test_initialize_pipeline_with_wrong_kwarg_type(
    unconnected_two_step_pipeline, empty_step
):
    """Test that pipeline initialization fails when a kwarg has a wrong type."""
    with pytest.raises(PipelineInterfaceError):
        unconnected_two_step_pipeline(step_1=1, step_2=empty_step())


def test_initialize_pipeline_with_missing_arg_step_brackets(
    unconnected_two_step_pipeline, generate_empty_steps
):
    """Test that pipeline initialization fails with missing arg brackets."""
    with pytest.raises(PipelineInterfaceError):
        empty_step_1, empty_step_2 = generate_empty_steps(2)
        unconnected_two_step_pipeline(empty_step_1, empty_step_2)


def test_initialize_pipeline_with_missing_kwarg_step_brackets(
    unconnected_two_step_pipeline, generate_empty_steps
):
    """Test that pipeline initialization fails with missing kwarg brackets."""
    with pytest.raises(PipelineInterfaceError):
        empty_step_1, empty_step_2 = generate_empty_steps(2)
        unconnected_two_step_pipeline(step_1=empty_step_1, step_2=empty_step_2)


def test_setting_step_parameter_with_config_object():
    """Test whether step parameters can be set using a config object."""
    config_value = 0
    pipeline_instance = create_pipeline_with_param_value(config_value)
    step_instance = pipeline_instance.steps["step_"]

    assert step_instance.configuration.parameters["value"] == config_value


def test_calling_a_pipeline_twice_raises_no_exception(
    one_step_pipeline, empty_step
):
    """Tests that calling one pipeline instance twice does not raise any exception."""
    pipeline_instance = one_step_pipeline(empty_step())

    with does_not_raise():
        pipeline_instance.run(unlisted=True)
        pipeline_instance.run(unlisted=True)


@step
def step_with_output() -> int:
    return 1


@step
def step_with_three_inputs(a: int, b: int, c: int) -> None:
    pass


def test_step_can_receive_the_same_input_artifact_multiple_times():
    """Tests that a step can receive the same input artifact multiple times."""

    @pipeline
    def test_pipeline(step_1, step_2):
        output = step_1()
        step_2(a=output, b=output, c=output)

    pipeline_instance = test_pipeline(
        step_1=step_with_output(), step_2=step_with_three_inputs()
    )

    with does_not_raise():
        pipeline_instance.run(unlisted=True)


def test_pipeline_does_not_need_to_call_all_steps(empty_step):
    """Tests that a pipeline does not have to call all it's steps."""

    @pipeline
    def test_pipeline(step_1, step_2):
        step_1()
        # don't call step_2

    pipeline_instance = test_pipeline(
        step_1=empty_step(), step_2=empty_step(name="other_name")
    )

    with does_not_raise():
        pipeline_instance.run(unlisted=True)


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
        one_step_pipeline(step_that_requires_step_operator()).run(
            unlisted=True
        )


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
    def p():
        pass

    pipeline_instance = p()
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
    pipeline_instance = one_step_pipeline(empty_step())

    schedule = Schedule(cron_expression="5 * * * *")
    pipeline_instance.run(run_name="run_name", schedule=schedule)

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
    pipeline_instance = one_step_pipeline(empty_step())

    schedule = Schedule(cron_expression="5 * * * *")

    config_path = tmp_path / "config.yaml"
    expected_run_config = PipelineRunConfiguration(
        run_name="run_name", schedule=schedule
    )
    config_path.write_text(expected_run_config.yaml())

    pipeline_instance.run(config_path=str(config_path))
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
    pipeline_instance = one_step_pipeline(empty_step())

    schedule = Schedule(cron_expression="5 * * * *")

    config_path = tmp_path / "config.yaml"
    file_config = PipelineRunConfiguration(
        run_name="run_name_in_file", schedule=schedule
    )
    config_path.write_text(file_config.yaml())

    pipeline_instance.run(
        config_path=str(config_path),
        run_name="run_name_in_code",
    )

    expected_run_config = PipelineRunConfiguration(
        run_name="run_name_in_code",
        schedule=Schedule(cron_expression="5 * * * *"),
    )
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
def pipeline_with_cache_enabled(step_1, step_2) -> None:
    step_1()
    step_2()


@pipeline(enable_cache=False)
def pipeline_with_cache_disabled(
    step_1,
    step_2,
) -> None:
    step_1()
    step_2()


def test_setting_enable_cache_at_run_level_overrides_all_decorator_values(
    mocker: MockFixture,
):
    """Test that `pipeline.run(enable_cache=...)` overrides decorator values."""

    def assert_cache_enabled(deployment: PipelineDeploymentBase):
        assert deployment.pipeline_configuration.enable_cache is True
        for step_ in deployment.step_configurations.values():
            assert step_.config.enable_cache is True

    def assert_cache_disabled(
        deployment: PipelineDeploymentBase,
    ):
        assert deployment.pipeline_configuration.enable_cache is False
        for step_ in deployment.step_configurations.values():
            assert step_.config.enable_cache is False

    cache_enabled_mock = mocker.MagicMock(side_effect=assert_cache_enabled)
    cache_disabled_mock = mocker.MagicMock(side_effect=assert_cache_disabled)

    # Test that `enable_cache=True` overrides all decorator values
    mocker.patch(
        "zenml.stack.stack.Stack.deploy_pipeline", new=cache_enabled_mock
    )
    pipeline_instance = pipeline_with_cache_disabled(
        step_1=step_with_cache_enabled(),
        step_2=step_with_cache_disabled(),
    )
    pipeline_instance.run(unlisted=True, enable_cache=True)
    assert cache_enabled_mock.call_count == 1

    # Test that `enable_cache=False` overrides all decorator values
    mocker.patch(
        "zenml.stack.stack.Stack.deploy_pipeline", new=cache_disabled_mock
    )
    pipeline_instance = pipeline_with_cache_enabled(
        step_1=step_with_cache_enabled(),
        step_2=step_with_cache_disabled(),
    )
    pipeline_instance.run(unlisted=True, enable_cache=False)
    assert cache_disabled_mock.call_count == 1


def test_unique_identifier_considers_spec(empty_step):
    """Tests that the unique pipeline ID depends on the pipeline spec."""

    @pipeline
    def p(s1, s2):
        s1()
        s2()
        s2.after(s1)

    step_1 = empty_step(name="step_1")
    step_2 = empty_step(name="step_2")
    pipeline_instance = p(step_1, step_2)

    pipeline_instance.prepare()
    spec = Compiler().compile_spec(pipeline=pipeline_instance)
    id_ = pipeline_instance._compute_unique_identifier(spec)

    new_instance = p(step_1, step_with_cache_enabled())
    new_instance.prepare()
    new_spec = Compiler().compile_spec(pipeline=new_instance)
    new_id = new_instance._compute_unique_identifier(new_spec)

    assert spec != new_spec
    assert id_ != new_id


def test_unique_identifier_considers_step_source_code(
    one_step_pipeline, empty_step, mocker
):
    """Tests that the unique pipeline ID depends on the step source code."""
    step_instance = empty_step()
    pipeline_instance = one_step_pipeline(step_instance)

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


def test_latest_version_fetching(
    mocker,
    empty_pipeline,  # noqa: F811
    create_pipeline_model,
):
    """Tests fetching the latest pipeline version."""
    mock_list_pipelines = mocker.patch(
        "zenml.client.Client.list_pipelines",
        return_value=Page(
            index=1,
            max_size=1,
            total_pages=1,
            total=0,
            items=[],
        ),
    )

    pipeline_instance = empty_pipeline
    assert pipeline_instance._get_latest_version() is None
    mock_list_pipelines.assert_called_with(
        name=pipeline_instance.name, sort_by="desc:created", size=1
    )

    unversioned_pipeline_model = create_pipeline_model(version="UNVERSIONED")
    mock_list_pipelines = mocker.patch(
        "zenml.client.Client.list_pipelines",
        return_value=Page(
            index=1,
            max_size=1,
            total_pages=1,
            total=1,
            items=[unversioned_pipeline_model],
        ),
    )

    assert pipeline_instance._get_latest_version() is None

    pipeline_model = create_pipeline_model(version="3")
    mock_list_pipelines = mocker.patch(
        "zenml.client.Client.list_pipelines",
        return_value=Page(
            index=1,
            max_size=1,
            total_pages=1,
            total=1,
            items=[pipeline_model],
        ),
    )

    assert pipeline_instance._get_latest_version() == 3


def test_registering_new_pipeline_version(
    mocker,
    empty_pipeline,  # noqa: F811
):
    """Tests registering a new pipeline version."""
    mocker.patch(
        "zenml.client.Client.list_pipelines",
        return_value=Page(
            index=1,
            max_size=1,
            total_pages=1,
            total=0,
            items=[],
        ),
    )
    mock_create_pipeline = mocker.patch(
        "zenml.zen_stores.sql_zen_store.SqlZenStore.create_pipeline",
    )

    pipeline_instance = empty_pipeline
    pipeline_instance.register()
    _, call_kwargs = mock_create_pipeline.call_args
    assert call_kwargs["pipeline"].version == "1"
    mock_create_pipeline.reset_mock()

    mocker.patch.object(Pipeline, "_get_latest_version", return_value=3)
    pipeline_instance.register()
    _, call_kwargs = mock_create_pipeline.call_args
    assert call_kwargs["pipeline"].version == "4"


def test_reusing_pipeline_version(
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


def test_loading_legacy_pipeline_from_model(create_pipeline_model):
    """Tests loading and running a pipeline from a model."""
    with open("my_steps.py", "w") as f:
        f.write(
            (
                "from zenml.steps import step\n"
                "@step\n"
                "def s1() -> int:\n"
                "  return 1\n\n"
                "@step\n"
                "def s2(inp: int) -> None:\n"
                "  pass"
            )
        )

    spec = PipelineSpec.model_validate(
        {
            "version": "0.3",
            "steps": [
                {
                    "source": "my_steps.s1",
                    "upstream_steps": [],
                    "pipeline_parameter_name": "step_1",
                },
                {
                    "source": "my_steps.s2",
                    "upstream_steps": ["step_1"],
                    "inputs": {
                        "inp": {"step_name": "step_1", "output_name": "output"}
                    },
                    "pipeline_parameter_name": "step_2",
                },
            ],
        }
    )
    pipeline_model = create_pipeline_model(spec=spec)

    pipeline_instance = BasePipeline.from_model(pipeline_model)
    assert Compiler().compile_spec(pipeline_instance) == spec
    assert pipeline_instance.name == pipeline_model.name

    with does_not_raise():
        pipeline_instance.run()

    # Invalid source
    spec = PipelineSpec.model_validate(
        {
            "version": "0.3",
            "steps": [
                {
                    "source": "WRONG_MODULE.s1",
                    "upstream_steps": [],
                    "pipeline_parameter_name": "step_1",
                },
            ],
        }
    )
    pipeline_model = create_pipeline_model(spec=spec)

    with pytest.raises(ImportError):
        pipeline_instance = BasePipeline.from_model(pipeline_model)

    # Missing upstream step
    spec = PipelineSpec.model_validate(
        {
            "version": "0.3",
            "steps": [
                {
                    "source": "my_steps.s1",
                    "upstream_steps": ["NONEXISTENT"],
                    "pipeline_parameter_name": "step_1",
                }
            ],
        }
    )
    pipeline_model = create_pipeline_model(spec=spec)

    with pytest.raises(RuntimeError):
        pipeline_instance = BasePipeline.from_model(pipeline_model)

    # Missing output
    spec = PipelineSpec.model_validate(
        {
            "version": "0.3",
            "steps": [
                {
                    "source": "my_steps.s1",
                    "upstream_steps": [],
                    "pipeline_parameter_name": "step_1",
                },
                {
                    "source": "my_steps.s2",
                    "upstream_steps": ["step_1"],
                    "inputs": {
                        "inp": {
                            "step_name": "step_1",
                            "output_name": "NONEXISTENT",
                        }
                    },
                    "pipeline_parameter_name": "step_2",
                },
            ],
        }
    )
    pipeline_model = create_pipeline_model(spec=spec)

    with pytest.raises(RuntimeError):
        pipeline_instance = BasePipeline.from_model(pipeline_model)

    # Wrong inputs
    spec = PipelineSpec.model_validate(
        {
            "version": "0.3",
            "steps": [
                {
                    "source": "my_steps.s1",
                    "upstream_steps": [],
                    "pipeline_parameter_name": "step_1",
                },
                {
                    "source": "my_steps.s2",
                    "upstream_steps": ["step_1"],
                    "inputs": {
                        "WRONG_INPUT_NAME": {
                            "step_name": "step_1",
                            "output_name": "output",
                        }
                    },
                    "pipeline_parameter_name": "step_2",
                },
            ],
        }
    )
    pipeline_model = create_pipeline_model(spec=spec)

    with pytest.raises(RuntimeError):
        pipeline_instance = BasePipeline.from_model(pipeline_model)


# TODO: move to deserialization utils tests
# def test_connect_method_generation(clean_workspace, create_pipeline_model):
#     """Tests dynamically generating the connect method from a model."""
#     with open("my_steps.py", "w") as f:
#         f.write(
#             (
#                 "from zenml.steps import step\n"
#                 "@step\n"
#                 "def s1() -> int:\n"
#                 "  return 1\n\n"
#                 "@step\n"
#                 "def s2(inp: int) -> None:\n"
#                 "  pass"
#             )
#         )

#     spec = PipelineSpec.model_validate(
#         {
#             "steps": [
#                 {
#                     "source": "my_steps.s1",
#                     "upstream_steps": [],
#                     "pipeline_parameter_name": "step_1",
#                 },
#                 {
#                     "source": "my_steps.s2",
#                     "upstream_steps": ["s1"],
#                     "inputs": {
#                         "inp": {"step_name": "s1", "output_name": "output"}
#                     },
#                     "pipeline_parameter_name": "step_2",
#                 },
#             ]
#         }
#     )
#     pipeline_model = create_pipeline_model(spec=spec)

#     connect_method = BasePipeline._generate_connect_method(pipeline_model)

#     arg_spec = inspect.getfullargspec(connect_method)
#     assert arg_spec.args == ["step_1", "step_2"]

#     steps = {
#         "step_1": BaseStep.load_from_source("my_steps.s1"),
#         "step_2": BaseStep.load_from_source("my_steps.s2"),
#     }

#     # Missing steps
#     with pytest.raises(TypeError):
#         connect_method()

#     # Additional arg
#     wrong_steps = steps.copy()
#     wrong_steps["step_3"] = wrong_steps["step_1"]
#     with pytest.raises(TypeError):
#         connect_method(**wrong_steps)

#     with does_not_raise():
#         connect_method(**steps)

#     # Reconfigure step name
#     steps = {
#         "step_1": BaseStep.load_from_source("my_steps.s1"),
#         "step_2": BaseStep.load_from_source("my_steps.s2"),
#     }
#     steps["step_1"].configure(name="new_name")
#     with pytest.raises(RuntimeError):
#         connect_method(**steps)


def test_loading_pipeline_from_old_spec_fails(create_pipeline_model):
    """Tests that loading a pipeline from a spec version <0.2 fails."""
    old_spec = PipelineSpec(version="0.1", steps=[])
    model = create_pipeline_model(spec=old_spec)

    with pytest.raises(ValueError):
        BasePipeline.from_model(model)


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

    _, _, schedule, _ = pipeline_instance._compile(
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
    _, _, _, build = pipeline_instance._compile(
        config_path=str(config_path_with_build_id), build=in_code_build_id
    )
    assert build == in_code_build_id
    # Config with build object
    _, _, _, build = pipeline_instance._compile(
        config_path=str(config_path_with_build), build=in_code_build_id
    )
    assert build == in_code_build_id

    in_code_build = PipelineBuildBase(
        images={"key": {"image": "image_name"}},
        is_local=False,
        contains_code=True,
    )
    # Config with ID
    _, _, _, build = pipeline_instance._compile(
        config_path=str(config_path_with_build_id), build=in_code_build
    )
    assert build == in_code_build
    # Config with build object
    _, _, _, build = pipeline_instance._compile(
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
    clean_client,
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

    scheduled_pipeline_instance = pipeline_instance.with_options(
        schedule=Schedule(cron_expression="*/5 * * * *")
    )
    scheduled_pipeline_instance()

    mock_create_run.assert_called_once()
    run_request = mock_create_run.call_args[0][0]  # First arg
    assert not is_placeholder_request(run_request)
