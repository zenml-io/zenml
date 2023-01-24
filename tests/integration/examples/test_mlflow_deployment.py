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

import pytest

from tests.integration.examples.utils import run_example
from zenml.post_execution import get_pipeline


def test_example(request: pytest.FixtureRequest) -> None:
    """Runs the mlflow_deployment example."""

    with run_example(
        request=request,
        name="mlflow_deployment",
        pipeline_name="inference_pipeline",
        run_count=1,
        step_count=4,
    ):
        from zenml.integrations.mlflow.services import MLFlowDeploymentService

        deployment_run = get_pipeline("continuous_deployment_pipeline").runs[
            -1
        ]

        service = deployment_run.get_step("model_deployer").output.read()
        assert isinstance(service, MLFlowDeploymentService)
