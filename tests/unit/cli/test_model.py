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
from typing import Any, ClassVar, Dict, List, Optional, Type
from uuid import UUID, uuid4

import pytest
from click.testing import CliRunner

from zenml.cli.cli import cli
from zenml.enums import StackComponentType
from zenml.model_deployers import BaseModelDeployer
from zenml.model_deployers.base_model_deployer import (
    DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
    BaseModelDeployerConfig,
    BaseModelDeployerFlavor,
)
from zenml.services import (
    BaseService,
    ServiceConfig,
    ServiceState,
    ServiceStatus,
    ServiceType,
)
from zenml.services.local.local_service_endpoint import (
    LocalDaemonServiceEndpoint,
)


class ConcreteModelDeployerConfig(BaseModelDeployerConfig):
    """Configuration for the Concrete model deployer."""

    @property
    def is_local(self) -> bool:
        return True


class ConcreteModelDeployerFlavor(BaseModelDeployerFlavor):
    """Concrete subclass of BaseModelDeployerFlavor that mocks the deploy_model method"""

    @property
    def name(self) -> str:
        return "local"

    @property
    def config_class(self) -> Type[ConcreteModelDeployerConfig]:
        return ConcreteModelDeployerConfig

    @property
    def implementation_class(self) -> Type["ConcreteModelDeployer"]:
        return ConcreteModelDeployer


class ConcreteModelDeployer(BaseModelDeployer):
    """Concrete subclass of BaseModelDeployer that mocks the deploy_model method"""

    NAME: ClassVar[str] = "LocalModelDeployer"
    FLAVOR: ClassVar[
        Type["BaseModelDeployerFlavor"]
    ] = ConcreteModelDeployerFlavor

    def deploy_model(
        self,
        config: ServiceConfig,
        replace: bool = False,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> BaseService:
        pass

    def find_model_server(
        self,
        running: bool = False,
        service_uuid: Optional[UUID] = None,
        pipeline_name: Optional[str] = None,
        pipeline_run_id: Optional[str] = None,
        pipeline_step_name: Optional[str] = None,
        model_name: Optional[str] = None,
        model_uri: Optional[str] = None,
        model_type: Optional[str] = None,
    ) -> List[BaseService]:
        breakpoint()

    def get_model_server_info(self, service: BaseService) -> Dict[str, Any]:
        pass

    def stop_model_server(
        self,
        service: BaseService,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> None:
        pass

    def start_model_server(
        self,
        service: BaseService,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> None:
        pass

    def delete_model_server(self, service: BaseService) -> None:
        pass


@pytest.fixture
def concrete_service_mock(mocker):
    service = mocker.MagicMock(spec=BaseService)
    service.SERVICE_TYPE = mocker.MagicMock(spec=ServiceType)
    service.uuid = f"123e4567-e89b-12d3-a456-426655440000"
    service.admin_state = random.choice(
        [ServiceState.INACTIVE, ServiceState.ACTIVE]
    )
    service.config = mocker.MagicMock(spec=ServiceConfig)
    service.config.model_uri = f"test_model_uri"
    service.config.model_name = f"test_model_name"
    service.config.pipeline_name = f"test_pipeline_name"
    service.config.pipeline_run_id = f"test_pipeline_run_id"
    service.config.pipeline_step_name = f"test_pipeline_step_name"
    service.status = mocker.MagicMock(spec=ServiceStatus)
    service.status.runtime_path = f"test_runtime_path"
    service.status.pid = 1234
    service.status.state = random.choice(
        [ServiceState.INACTIVE, ServiceState.ACTIVE]
    )
    service.status.last_error = None
    service.endpoint = mocker.MagicMock(spec=LocalDaemonServiceEndpoint)
    service.endpoint.prediction_url = f"test_url"
    return [service]


@pytest.fixture
def concrete_model_deployer(
    clean_project,
):
    """Returns a local model deployer."""
    return ConcreteModelDeployer(
        name="arias_deployer",
        id=uuid4(),
        config=ConcreteModelDeployerConfig(),
        flavor="local",
        type=StackComponentType.MODEL_DEPLOYER,
        user=clean_project.active_user.id,
        project=clean_project.active_project.id,
        created=datetime.now(),
        updated=datetime.now(),
    )


@pytest.fixture
def mock_info():
    return {
        "PREDICTION_URL": "test_url",
        "MODEL_URI": "test_model_uri",
        "MODEL_NAME": "test_model_name",
        "SERVICE_PATH": "/path/to/service",
        "DAEMON_PID": "1234",
    }


def test_list_models(
    mocker,
    concrete_service_mock,
    concrete_model_deployer,
    mock_info,
):
    # Get the list command
    runner = CliRunner()
    list_served_models = (
        cli.commands["model-deployer"].commands["models"].commands["list"]
    )

    # Patch the find_model_server method
    mocker.patch.object(
        ConcreteModelDeployer,
        "find_model_server",
        return_value=concrete_service_mock,
    )
    mocker.patch.object(
        ConcreteModelDeployer, "get_model_server_info", return_value=mock_info
    )

    # Run the command
    result = runner.invoke(list_served_models, obj=concrete_model_deployer)

    # Check the result
    assert result.exit_code == 0

    # Patch the find_model_server method
    mocker.patch.object(
        ConcreteModelDeployer, "find_model_server", return_value=[]
    )

    # Run the command
    result = runner.invoke(list_served_models, obj=concrete_model_deployer)

    # Check the result
    assert result.exit_code == 0


def test_describe_model(
    mocker,
    concrete_service_mock,
    concrete_model_deployer,
    mock_info,
):
    # Get the list command
    runner = CliRunner()
    describe_served_model = (
        cli.commands["model-deployer"].commands["models"].commands["describe"]
    )

    # Patch the find_model_server method
    mocker.patch.object(
        ConcreteModelDeployer,
        "find_model_server",
        return_value=[concrete_service_mock[0]],
    )
    mocker.patch.object(
        ConcreteModelDeployer, "get_model_server_info", return_value=mock_info
    )

    # Run the command
    result = runner.invoke(
        describe_served_model,
        [str(concrete_service_mock[0].uuid)],
        obj=concrete_model_deployer,
    )

    # Check the result
    assert result.exit_code == 0
    assert concrete_service_mock[0].uuid in result.output


def test_get_url(
    mocker,
    concrete_service_mock,
    concrete_model_deployer,
    mock_info,
):
    # Patch the find_model_server method
    mocker.patch.object(
        ConcreteModelDeployer,
        "find_model_server",
        return_value=[concrete_service_mock[0]],
    )
    mocker.patch.object(
        ConcreteModelDeployer, "get_model_server_info", return_value=mock_info
    )

    # Get the list command
    get_url = (
        cli.commands["model-deployer"].commands["models"].commands["get-url"]
    )

    # Run the command
    runner = CliRunner()
    result = runner.invoke(
        get_url,
        [str(concrete_service_mock[0].uuid)],
        obj=concrete_model_deployer,
    )
    assert result.exit_code == 0
    assert concrete_service_mock[0].endpoint.prediction_url in result.output


def test_start_model_service(
    mocker,
    concrete_service_mock,
    concrete_model_deployer,
    mock_info,
):
    # Patch the find_model_server method
    mocker.patch.object(
        ConcreteModelDeployer,
        "find_model_server",
        return_value=[concrete_service_mock[0]],
    )
    mocker.patch.object(
        ConcreteModelDeployer, "get_model_server_info", return_value=mock_info
    )
    mocker.patch.object(
        ConcreteModelDeployer, "start_model_server", return_value=None
    )

    # Get the list command
    start_model = (
        cli.commands["model-deployer"].commands["models"].commands["start"]
    )

    # Run the command
    runner = CliRunner()
    result = runner.invoke(
        start_model,
        [str(concrete_service_mock[0].uuid)],
        obj=concrete_model_deployer,
    )
    assert result.exit_code == 0
    assert str(concrete_service_mock[0]) in result.output


def test_stop_model_service(
    mocker,
    concrete_service_mock,
    concrete_model_deployer,
    mock_info,
):
    # Patch the find_model_server method
    mocker.patch.object(
        ConcreteModelDeployer,
        "find_model_server",
        return_value=[concrete_service_mock[0]],
    )
    mocker.patch.object(
        ConcreteModelDeployer, "get_model_server_info", return_value=mock_info
    )
    mocker.patch.object(
        ConcreteModelDeployer, "stop_model_server", return_value=None
    )

    # Get the list command
    stop_model = (
        cli.commands["model-deployer"].commands["models"].commands["stop"]
    )

    # Run the command
    runner = CliRunner()
    result = runner.invoke(
        stop_model,
        [str(concrete_service_mock[0].uuid)],
        obj=concrete_model_deployer,
    )
    assert result.exit_code == 0
    assert str(concrete_service_mock[0]) in result.output


def test_delete_model_service(
    mocker,
    concrete_service_mock,
    concrete_model_deployer,
    mock_info,
):
    # Patch the find_model_server method
    mocker.patch.object(
        ConcreteModelDeployer,
        "find_model_server",
        return_value=[concrete_service_mock[0]],
    )
    mocker.patch.object(
        ConcreteModelDeployer, "get_model_server_info", return_value=mock_info
    )
    mocker.patch.object(
        ConcreteModelDeployer, "delete_model_server", return_value=None
    )

    # Get the list command
    delete_model = (
        cli.commands["model-deployer"].commands["models"].commands["delete"]
    )

    # Run the command
    runner = CliRunner()
    result = runner.invoke(
        delete_model,
        [str(concrete_service_mock[0].uuid)],
        obj=concrete_model_deployer,
    )
    assert result.exit_code == 0
    assert str(concrete_service_mock[0]) in result.output


def test_get_model_server_logs(
    mocker,
    concrete_service_mock,
    concrete_model_deployer,
    mock_info,
):
    # Patch the find_model_server method
    mocker.patch.object(
        ConcreteModelDeployer,
        "find_model_server",
        return_value=[concrete_service_mock[0]],
    )
    mocker.patch.object(
        ConcreteModelDeployer, "get_model_server_info", return_value=mock_info
    )
    mocker.patch.object(
        ConcreteModelDeployer, "get_model_server_logs", return_value=""
    )

    # Get the list command
    get_logs = (
        cli.commands["model-deployer"].commands["models"].commands["logs"]
    )

    # Run the command
    runner = CliRunner()
    result = runner.invoke(
        get_logs,
        [str(concrete_service_mock[0].uuid)],
        obj=concrete_model_deployer,
    )
    assert result.exit_code == 0
    assert "" in result.output
