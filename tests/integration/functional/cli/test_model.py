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
import random
from datetime import datetime
from uuid import uuid4

import pytest
from click.testing import CliRunner

from zenml.cli.cli import cli
from zenml.enums import StackComponentType
from zenml.integrations.mlflow.flavors.mlflow_model_deployer_flavor import (
    MLFlowModelDeployerConfig,
)
from zenml.integrations.mlflow.model_deployers.mlflow_model_deployer import (
    MLFlowModelDeployer,
)
from zenml.integrations.mlflow.services.mlflow_deployment import (
    MLFlowDeploymentEndpoint,
)
from zenml.services import (
    BaseService,
    ServiceConfig,
    ServiceState,
    ServiceStatus,
    ServiceType,
)


@pytest.fixture
def mlflow_service_mock(mocker):
    services = []
    for i in range(3):
        service = mocker.MagicMock(spec=BaseService)
        service.SERVICE_TYPE = mocker.MagicMock(spec=ServiceType)
        service.uuid = f"123e4567-e89b-12d3-a456-42665544{i:04d}"
        service.admin_state = random.choice(
            [ServiceState.INACTIVE, ServiceState.ACTIVE]
        )
        service.config = mocker.MagicMock(spec=ServiceConfig)
        service.config.model_uri = f"test_model_uri_{i}"
        service.config.model_name = f"test_model_name_{i}"
        service.config.pipeline_name = f"test_pipeline_name_{i}"
        service.config.pipeline_run_id = f"test_pipeline_run_id_{i}"
        service.config.pipeline_step_name = f"test_pipeline_step_name_{i}"
        service.status = mocker.MagicMock(spec=ServiceStatus)
        service.status.runtime_path = f"test_runtime_path_{i}"
        service.status.pid = 1234 + i
        service.status.state = random.choice(
            [ServiceState.INACTIVE, ServiceState.ACTIVE]
        )
        service.status.last_error = None
        service.endpoint = mocker.MagicMock(spec=MLFlowDeploymentEndpoint)
        service.endpoint.prediction_url = f"http://test_url_{i}"
        service.endpoint.url = f"http://test_url_{i}"
        services.append(service)
    return services


@pytest.fixture
def mlflow_model_deployer(
    clean_project,
):
    """Returns a local orchestrator."""
    return MLFlowModelDeployer(
        name="arias_orchestrator",
        id=uuid4(),
        config=MLFlowModelDeployerConfig(),
        flavor="mlflow",
        type=StackComponentType.MODEL_DEPLOYER,
        user=clean_project.active_user.id,
        project=clean_project.active_project.id,
        created=datetime.now(),
        updated=datetime.now(),
    )


def test_list_models(
    mocker,
    mlflow_service_mock,
    mlflow_model_deployer,
):
    # Patch the find_model_server method
    mocker.patch(
        "zenml.integrations.mlflow.model_deployers.mlflow_model_deployer.MLFlowModelDeployer.find_model_server",
        return_value=mlflow_service_mock,  # The return value of the patched method
    )

    # Get the list command
    list_served_models = (
        cli.commands["model-deployer"].commands["models"].commands["list"]
    )

    # Run the command
    runner = CliRunner()
    result = runner.invoke(list_served_models, obj=mlflow_model_deployer)
    assert result.exit_code == 0


def test_describe_model(
    mocker,
    mlflow_service_mock,
    mlflow_model_deployer,
):
    # Patch the find_model_server method
    mocker.patch(
        "zenml.integrations.mlflow.model_deployers.mlflow_model_deployer.MLFlowModelDeployer.find_model_server",
        return_value=[
            mlflow_service_mock[0]
        ],  # The return value of the patched method
    )

    # Get the list command
    describe_served_model = (
        cli.commands["model-deployer"].commands["models"].commands["describe"]
    )

    # Run the command
    runner = CliRunner()
    result = runner.invoke(
        describe_served_model,
        [str(mlflow_service_mock[0].uuid)],
        obj=mlflow_model_deployer,
    )
    assert result.exit_code == 0
    assert mlflow_service_mock[0].uuid in result.output


def test_get_url(
    mocker,
    mlflow_service_mock,
    mlflow_model_deployer,
):
    # Patch the find_model_server method
    mocker.patch(
        "zenml.integrations.mlflow.model_deployers.mlflow_model_deployer.MLFlowModelDeployer.find_model_server",
        return_value=[
            mlflow_service_mock[0]
        ],  # The return value of the patched method
    )

    # Get the list command
    get_url = (
        cli.commands["model-deployer"].commands["models"].commands["get-url"]
    )

    # Run the command
    runner = CliRunner()
    result = runner.invoke(
        get_url, [str(mlflow_service_mock[0].uuid)], obj=mlflow_model_deployer
    )
    assert result.exit_code == 0
    assert mlflow_service_mock[0].endpoint.url in result.output
