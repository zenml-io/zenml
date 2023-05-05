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
from zenml.post_execution.pipeline import get_pipeline


def test_example(request: pytest.FixtureRequest) -> None:
    """Runs the quickstart_py37 example."""

    with run_example(
        request=request,
        name="quickstart_py37",
        pipelines={"training_pipeline": (1, 5), "inference_pipeline": (1, 5)},
    ):
        from zenml.integrations.mlflow.services import MLFlowDeploymentService

        training_run = get_pipeline("training_pipeline").runs[0]

        service = training_run.get_step("model_deployer").output.read()
        assert isinstance(service, MLFlowDeploymentService)

        if service.is_running:
            service.stop(timeout=60)
