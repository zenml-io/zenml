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


from zenml.config.step_configurations import InputSpec, StepSpec


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
    """Tests the inputs don't affect the step spec equality."""
    assert StepSpec(
        source="src",
        upstream_steps=[],
        inputs={"key": InputSpec(step_name="s", output_name="o")},
    ) == StepSpec(
        source="src",
        upstream_steps=[],
        inputs={},
    )
