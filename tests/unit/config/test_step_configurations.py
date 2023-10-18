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


from uuid import uuid4

from zenml.artifacts.external_artifact_config import (
    ExternalArtifactConfiguration,
)
from zenml.config.step_configurations import (
    InputSpec,
    PartialStepConfiguration,
    StepSpec,
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


def test_step_spec_pipeline_parameter_name_equality():
    """Tests the step spec equality operator regarding the pipeline parameter
    name."""
    assert StepSpec(
        source="src", upstream_steps=[], pipeline_parameter_name="name"
    ) != StepSpec(
        source="src",
        upstream_steps=[],
        pipeline_parameter_name="different_name",
    )


def test_step_config_can_recover_from_json():
    """Tests that step spec can be recovered from json."""
    uuid = uuid4()
    from_json = PartialStepConfiguration.parse_raw(
        '{"name":"foo","external_input_artifacts": {"bar":"'
        + str(uuid)
        + '"}}'
    )
    from_object = PartialStepConfiguration(
        name="foo", external_input_artifacts={"bar": uuid}
    )
    assert from_json == from_object

    from_json = PartialStepConfiguration.parse_raw(
        '{"name":"foo","external_input_artifacts": {"bar":{"id":"'
        + str(uuid)
        + '"}}}'
    )
    from_object = PartialStepConfiguration(
        name="foo",
        external_input_artifacts={
            "bar": ExternalArtifactConfiguration(id=uuid)
        },
    )
    assert from_json == from_object
