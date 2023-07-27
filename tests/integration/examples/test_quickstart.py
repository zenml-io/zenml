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
from zenml.client import Client
from zenml.integrations.mlflow.model_registries.mlflow_model_registry import (
    MLFlowModelRegistry,
)


def test_example(request: pytest.FixtureRequest) -> None:
    """Runs the quickstart example."""

    with run_example(
        request=request,
        name="quickstart",
        pipelines={
            "train_and_register_model_pipeline": (1, 5),
            "deploy_and_predict": (1, 4),
        },
    ):
        # activate the stack set up and used by the example
        client = Client()
        model_registry = client.active_stack.model_registry
        assert isinstance(model_registry, MLFlowModelRegistry)

        # fetch the MLflow registered model
        registered_model = model_registry.get_model(
            name="zenml-quickstart-model",
        )
        assert registered_model is not None

        # fetch the MLflow registered model version
        registered_model_version = model_registry.get_model_version(
            name="zenml-quickstart-model",
            version=1,
        )
        assert registered_model_version is not None

        # Check that the deployment service is running
        from zenml.integrations.mlflow.services import MLFlowDeploymentService

        training_run = client.get_pipeline("deploy_and_predict").last_run

        service = training_run.steps[
            "mlflow_model_registry_deployer_step"
        ].output.load()
        assert isinstance(service, MLFlowDeploymentService)

        if service.is_running:
            service.stop(timeout=180)
