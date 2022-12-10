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


from zenml.config.step_configurations import StepSpec


def test_step_spec_equality():
    """Tests the step spec equality operator."""
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
