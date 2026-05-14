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


from zenml.config.pipeline_spec import PipelineSpec
from zenml.config.step_configurations import (
    InputSpec,
    Step,
    StepConfiguration,
    StepSpec,
)
from zenml.config.step_execution_spec import (
    StepExecutionLanguage,
    StepExecutionProtocol,
    StepExecutionSpec,
)
from zenml.zenbabel.adapters import PORTABLE_STEP_ADAPTER_SOURCE


def _portable_execution_spec(source_identity: str) -> StepExecutionSpec:
    """Create a portable execution spec for tests."""
    return StepExecutionSpec(
        language=StepExecutionLanguage.TYPESCRIPT,
        protocol=StepExecutionProtocol.ZENML_PORTABLE_JSON_V1,
        command=["node", "/app/dist/steps/score.js"],
        source_identity=source_identity,
    )


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


def test_step_spec_execution_spec_equality():
    """Tests equality for portable step execution specs."""
    adapter_source = PORTABLE_STEP_ADAPTER_SOURCE

    assert StepSpec(
        source=adapter_source,
        upstream_steps=[],
        execution_spec=_portable_execution_spec("ts/src/score.ts#score"),
    ) == StepSpec(
        source=adapter_source,
        upstream_steps=[],
        execution_spec=_portable_execution_spec("ts/src/score.ts#score"),
    )

    assert StepSpec(
        source=adapter_source,
        upstream_steps=[],
        execution_spec=_portable_execution_spec("ts/src/score.ts#score"),
    ) != StepSpec(
        source=adapter_source,
        upstream_steps=[],
        execution_spec=_portable_execution_spec("ts/src/score.ts#other"),
    )


def test_python_pipeline_spec_serialization_omits_empty_execution_spec():
    """Tests that Python-only specs do not get execution spec churn."""
    spec = PipelineSpec(
        steps=[
            StepSpec(
                source="tests.unit.config.test_step_configurations.step",
                upstream_steps=[],
                invocation_id="step",
            )
        ]
    )

    assert spec.version == "0.5"
    assert "execution_spec" not in spec.model_dump(mode="json")["steps"][0]
    assert "execution_spec" not in spec.json_with_string_sources

    step = Step(
        spec=spec.steps[0],
        config=StepConfiguration(name="step"),
        step_config_overrides=StepConfiguration(name="step"),
    )
    assert "execution_spec" not in step.model_dump_json(exclude={"config"})


def test_portable_pipeline_spec_serialization_sets_version_and_identity():
    """Tests deterministic serialization for portable step specs."""
    spec = PipelineSpec(
        steps=[
            StepSpec(
                source=PORTABLE_STEP_ADAPTER_SOURCE,
                upstream_steps=[],
                invocation_id="score",
                execution_spec=_portable_execution_spec(
                    "examples/zenbabel/ts/src/steps/score.ts#score"
                ),
            )
        ]
    )

    dumped = spec.model_dump(mode="json")
    assert spec.version == "0.6"
    assert dumped["version"] == "0.6"
    assert dumped["steps"][0]["execution_spec"] == {
        "language": "typescript",
        "protocol": "zenml-portable-json-v1",
        "command": ["node", "/app/dist/steps/score.js"],
        "source_identity": "examples/zenbabel/ts/src/steps/score.ts#score",
    }

    serialized = spec.json_with_string_sources
    assert serialized == spec.json_with_string_sources
    assert '"version": "0.6"' in serialized
    assert "examples/zenbabel/ts/src/steps/score.ts#score" in serialized
