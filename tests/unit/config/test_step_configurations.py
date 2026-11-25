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


from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.step_configurations import (
    InputSpec,
    Step,
    StepConfiguration,
    StepSpec,
)

_HOOK_SOURCES = {
    "start_hook_source": "module.on_start",
    "end_hook_source": "module.on_end",
    "success_hook_source": "module.on_success",
    "failure_hook_source": "module.on_failure",
}


def test_step_spec_source_equality():
    """Tests the step spec equality operator regarding the source."""
    assert StepSpec(
        source="zenml.integrations.airflow.AirflowIntegration",
        upstream_steps=[],
        inputs={},
    ) == StepSpec(
        source="zenml.integrations.airflow.AirflowIntegration@zenml_1.0.0",
        upstream_steps=[],
        inputs={},
    )
    assert StepSpec(
        source="zenml.integrations.airflow.AirflowIntegration",
        upstream_steps=[],
        inputs={},
    ) != StepSpec(
        source="zenml.integrations.airflow.NotAirflowIntegration",
        upstream_steps=[],
        inputs={},
    )


def test_step_spec_upstream_steps_equality():
    """Tests the step spec equality operator regarding the upstream steps."""
    assert StepSpec(
        source="src",
        upstream_steps=["s1"],
        inputs={},
    ) == StepSpec(
        source="src",
        upstream_steps=["s1"],
        inputs={},
    )
    assert StepSpec(
        source="src",
        upstream_steps=["s1"],
        inputs={},
    ) != StepSpec(
        source="src",
        upstream_steps=["s2"],
        inputs={},
    )


def test_step_spec_inputs_equality():
    """Tests the step spec equality operator regarding the inputs."""
    assert StepSpec(
        source="src",
        upstream_steps=[],
        inputs={"key": InputSpec(step_name="s", output_name="o")},
    ) == StepSpec(
        source="src",
        upstream_steps=[],
        inputs={"key": InputSpec(step_name="s", output_name="o")},
    )

    assert StepSpec(
        source="src",
        upstream_steps=[],
        inputs={"key": InputSpec(step_name="s", output_name="o")},
    ) != StepSpec(
        source="src",
        upstream_steps=[],
        inputs={},
    )


def test_step_spec_invocation_id_equality():
    """Tests the step spec equality operator regarding the invocation id."""
    assert StepSpec(
        source="src", upstream_steps=[], invocation_id="name"
    ) != StepSpec(
        source="src",
        upstream_steps=[],
        invocation_id="different_name",
    )


def test_step_spec_parameter_spec_equality():
    """Tests the step spec equality operator regarding the parameter spec."""
    assert StepSpec(
        source="src",
        upstream_steps=[],
        parameter_spec={"type": "object"},
    ) == StepSpec(
        source="src",
        upstream_steps=[],
        parameter_spec={"type": "object"},
    )
    assert StepSpec(
        source="src",
        upstream_steps=[],
        parameter_spec={"type": "object"},
    ) != StepSpec(
        source="src",
        upstream_steps=[],
        parameter_spec={},
    )


def test_apply_pipeline_configuration_propagates_hook_sources():
    """Tests that pipeline hook sources propagate to a step config."""
    pipeline_config = PipelineConfiguration(name="pipeline", **_HOOK_SOURCES)

    merged = StepConfiguration(name="step").apply_pipeline_configuration(
        pipeline_config, exclude_hook_sources=False
    )

    for field, import_path in _HOOK_SOURCES.items():
        assert getattr(merged, field).import_path == import_path


def test_from_dict_propagates_hook_sources():
    """Tests that hook sources propagate when reconstructing a step."""
    pipeline_config = PipelineConfiguration(name="pipeline", **_HOOK_SOURCES)

    step = Step.from_dict(
        data={
            "spec": StepSpec(source="module.step", upstream_steps=[]),
            "step_config_overrides": {"name": "step"},
        },
        pipeline_configuration=pipeline_config,
        exclude_hook_sources=False,
    )

    for field, import_path in _HOOK_SOURCES.items():
        assert getattr(step.config, field).import_path == import_path


def test_apply_pipeline_configuration_excludes_hook_sources():
    """Tests that hook sources are not propagated when excluded."""
    pipeline_config = PipelineConfiguration(name="pipeline", **_HOOK_SOURCES)

    merged = StepConfiguration(name="step").apply_pipeline_configuration(
        pipeline_config, exclude_hook_sources=True
    )

    for field in _HOOK_SOURCES:
        assert getattr(merged, field) is None


def test_apply_pipeline_configuration_exclude_keeps_step_own_hooks():
    """Tests that a step keeps its own hook sources when pipeline ones are excluded."""
    pipeline_config = PipelineConfiguration(name="pipeline", **_HOOK_SOURCES)

    merged = StepConfiguration(
        name="step", start_hook_source="module.step_on_start"
    ).apply_pipeline_configuration(pipeline_config, exclude_hook_sources=True)

    assert merged.start_hook_source.import_path == "module.step_on_start"
    assert merged.end_hook_source is None


def test_from_dict_excludes_hook_sources():
    """Tests that hook sources are not propagated when reconstructing with exclude."""
    pipeline_config = PipelineConfiguration(name="pipeline", **_HOOK_SOURCES)

    step = Step.from_dict(
        data={
            "spec": StepSpec(source="module.step", upstream_steps=[]),
            "step_config_overrides": {"name": "step"},
        },
        pipeline_configuration=pipeline_config,
        exclude_hook_sources=True,
    )

    for field in _HOOK_SOURCES:
        assert getattr(step.config, field) is None
