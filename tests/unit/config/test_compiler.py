#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
import pytest

from zenml.config import ResourceSettings
from zenml.config.base_settings import BaseSettings
from zenml.config.compiler import Compiler
from zenml.config.pipeline_configurations import PipelineRunConfiguration
from zenml.config.step_configurations import StepConfigurationUpdate
from zenml.exceptions import PipelineInterfaceError, StackValidationError
from zenml.pipelines import pipeline


def test_compiling_pipeline_with_duplicate_step_names_fails(
    unconnected_two_step_pipeline, empty_step, local_stack
):
    """Tests that compiling a pipeline with two steps with the same name
    fails."""
    pipeline_instance = unconnected_two_step_pipeline(
        empty_step(), empty_step()
    )
    with pytest.raises(PipelineInterfaceError):
        Compiler().compile(
            pipeline=pipeline_instance,
            stack=local_stack,
            run_configuration=PipelineRunConfiguration(),
        )


def test_compiling_pipeline_with_invalid_run_name_fails(
    empty_pipeline, local_stack
):
    """Tests that compiling a pipeline with an invalid run name fails."""
    with pytest.raises(ValueError):
        Compiler().compile(
            pipeline=empty_pipeline(),
            stack=local_stack,
            run_configuration=PipelineRunConfiguration(
                run_name="{invalid_placeholder}"
            ),
        )


def test_compiling_pipeline_with_missing_step_operator(
    one_step_pipeline, empty_step, local_stack
):
    """Tests that compiling a pipeline with a missing step operator fails."""
    pipeline_instance = one_step_pipeline(
        empty_step().configure(step_operator="s")
    )
    with pytest.raises(StackValidationError):
        Compiler().compile(
            pipeline=pipeline_instance,
            stack=local_stack,
            run_configuration=PipelineRunConfiguration(),
        )


def test_compiling_pipeline_with_missing_experiment_tracker(
    one_step_pipeline, empty_step, local_stack
):
    """Tests that compiling a pipeline with a missing experiment tracker
    fails."""
    pipeline_instance = one_step_pipeline(
        empty_step().configure(experiment_tracker="e")
    )
    with pytest.raises(StackValidationError):
        Compiler().compile(
            pipeline=pipeline_instance,
            stack=local_stack,
            run_configuration=PipelineRunConfiguration(),
        )


def test_pipeline_and_steps_dont_get_modified_during_compilation(
    one_step_pipeline, empty_step, local_stack
):
    """Tests that the pipeline and step don't get modified during compilation."""
    step_instance = empty_step().configure(name="original_step_name")
    pipeline_instance = one_step_pipeline(step_instance).configure(
        enable_cache=True
    )
    run_config = PipelineRunConfiguration(
        enable_cache=False,
        steps={"step_": StepConfigurationUpdate(name="new_step_name")},
    )
    Compiler().compile(
        pipeline=pipeline_instance,
        stack=local_stack,
        run_configuration=run_config,
    )
    assert step_instance.name == "original_step_name"
    assert pipeline_instance.enable_cache is True


def test_compiling_pipeline_with_invalid_run_configuration(empty_pipeline):
    """Tests that compiling with a run configuration containing invalid steps
    fails."""
    run_config = PipelineRunConfiguration(
        steps={
            "non_existent_step": StepConfigurationUpdate(enable_cache=False)
        }
    )
    with pytest.raises(KeyError):
        Compiler()._apply_run_configuration(
            pipeline=empty_pipeline(), config=run_config
        )


def test_default_run_name():
    """Tests the default run name value."""
    assert (
        Compiler()._get_default_run_name(pipeline_name="my_pipeline")
        == "my_pipeline-{date}-{time}"
    )


def test_step_sorting(empty_step, local_stack):
    """Tests that the steps in the compiled deployment are sorted correctly."""

    @pipeline
    def sequential_pipeline(step_1, step_2):
        step_1()
        step_2()
        step_2.after(step_1)

    pipeline_instance = sequential_pipeline(
        step_2=empty_step(name="step_2"), step_1=empty_step(name="step_1")
    )
    deployment, _ = Compiler().compile(
        pipeline=pipeline_instance,
        stack=local_stack,
        run_configuration=PipelineRunConfiguration(),
    )
    assert list(deployment.steps.keys()) == ["step_1", "step_2"]


def test_stack_component_settings_merging(
    mocker, one_step_pipeline, empty_step, local_stack
):
    """Tests the merging of stack component settings defined on steps,
    pipelines, the run configuration and the stack component config."""

    class StubSettings(BaseSettings):
        component_value: int = 0
        pipeline_value: int = 0
        step_value: int = 0

    step_instance = empty_step()
    pipeline_instance = one_step_pipeline(step_instance)

    component_settings = StubSettings(component_value=1)
    pipeline_settings = StubSettings(pipeline_value=1)
    run_pipeline_settings = StubSettings(pipeline_value=2)
    step_settings = StubSettings(step_value=1)
    run_step_settings = StubSettings(step_value=2)

    orchestrator_class = type(local_stack.orchestrator)
    mocker.patch.object(
        orchestrator_class,
        "settings_class",
        new_callable=mocker.PropertyMock,
        return_value=StubSettings,
    )
    mocker.patch.object(
        orchestrator_class,
        "config",
        new_callable=mocker.PropertyMock,
        return_value=component_settings,
    )

    pipeline_instance.configure(
        settings={"orchestrator.default": pipeline_settings}
    )
    step_instance.configure(settings={"orchestrator.default": step_settings})
    run_config = PipelineRunConfiguration(
        settings={"orchestrator.default": run_pipeline_settings},
        steps={
            "step_": StepConfigurationUpdate(
                settings={"orchestrator.default": run_step_settings}
            )
        },
    )

    deployment, _ = Compiler().compile(
        pipeline=pipeline_instance,
        stack=local_stack,
        run_configuration=run_config,
    )

    compiled_pipeline_settings = StubSettings.parse_obj(
        deployment.pipeline.settings["orchestrator.default"]
    )
    assert compiled_pipeline_settings.component_value == 1
    assert compiled_pipeline_settings.pipeline_value == 2
    assert compiled_pipeline_settings.step_value == 0

    compiled_step_settings = StubSettings.parse_obj(
        deployment.steps["step_"].config.settings["orchestrator.default"]
    )
    assert compiled_pipeline_settings.component_value == 1
    assert compiled_step_settings.pipeline_value == 2
    assert compiled_step_settings.step_value == 2


def test_general_settings_merging(one_step_pipeline, empty_step, local_stack):
    """Tests the merging of general settings defined on steps, pipelines and the
    run configuration."""
    step_instance = empty_step()
    pipeline_instance = one_step_pipeline(step_instance)

    pipeline_settings = ResourceSettings(cpu_count=42, memory="1KB")
    run_pipeline_settings = ResourceSettings(cpu_count=100)
    step_settings = ResourceSettings(gpu_count=11)
    run_step_settings = ResourceSettings(memory="9TB")

    pipeline_instance.configure(settings={"resources": pipeline_settings})
    step_instance.configure(settings={"resources": step_settings})
    run_config = PipelineRunConfiguration(
        settings={"resources": run_pipeline_settings},
        steps={
            "step_": StepConfigurationUpdate(
                settings={"resources": run_step_settings}
            )
        },
    )

    deployment, _ = Compiler().compile(
        pipeline=pipeline_instance,
        stack=local_stack,
        run_configuration=run_config,
    )

    compiled_pipeline_settings = ResourceSettings.parse_obj(
        deployment.pipeline.settings["resources"]
    )

    assert compiled_pipeline_settings.cpu_count == 100
    assert compiled_pipeline_settings.gpu_count is None
    assert compiled_pipeline_settings.memory == "1KB"

    compiled_step_settings = ResourceSettings.parse_obj(
        deployment.steps["step_"].config.settings["resources"]
    )

    assert compiled_step_settings.cpu_count == 100
    assert compiled_step_settings.gpu_count == 11
    assert compiled_step_settings.memory == "9TB"


def test_extra_merging(one_step_pipeline, empty_step, local_stack):
    """Tests the merging of extra values defined on steps, pipelines and the
    run configuration."""
    step_instance = empty_step()
    pipeline_instance = one_step_pipeline(step_instance)

    pipeline_extra = {"p1": 0, "p2": 0, "p3": 0}
    run_pipeline_extra = {"p2": 1, "p4": 0}
    step_extra = {"s1": 0, "s2": 0, "p3": 1}
    run_step_extra = {"s2": 1, "p4": 1}

    pipeline_instance.configure(extra=pipeline_extra)
    step_instance.configure(extra=step_extra)
    run_config = PipelineRunConfiguration(
        extra=run_pipeline_extra,
        steps={"step_": StepConfigurationUpdate(extra=run_step_extra)},
    )

    deployment, _ = Compiler().compile(
        pipeline=pipeline_instance,
        stack=local_stack,
        run_configuration=run_config,
    )

    compiled_pipeline_extra = deployment.pipeline.extra
    assert compiled_pipeline_extra == {"p1": 0, "p2": 1, "p3": 0, "p4": 0}

    compiled_step_extra = deployment.steps["step_"].config.extra
    assert compiled_step_extra == {
        "p1": 0,
        "p2": 1,
        "p3": 1,
        "p4": 1,
        "s1": 0,
        "s2": 1,
    }


def test_stack_component_settings_for_missing_component_are_ignored(
    one_step_pipeline, empty_step, local_stack
):
    """Tests that stack component settings for a component that is not part
    of the stack get ignored."""
    step_instance = empty_step()
    pipeline_instance = one_step_pipeline(step_instance)

    settings = {"orchestrator.not_a_flavor": {"some_key": "some_value"}}

    pipeline_instance.configure(settings=settings)
    step_instance.configure(settings=settings)
    run_config = PipelineRunConfiguration(
        settings=settings,
        steps={"step_": StepConfigurationUpdate(settings=settings)},
    )

    deployment, _ = Compiler().compile(
        pipeline=pipeline_instance,
        stack=local_stack,
        run_configuration=run_config,
    )

    assert "orchestrator.not_a_flavor" not in deployment.pipeline.settings
    assert (
        "orchestrator.not_a_flavor"
        not in deployment.steps["step_"].config.settings
    )
