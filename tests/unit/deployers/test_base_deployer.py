#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Tests for deployment polling feedback and lifecycle outcomes."""

from datetime import datetime
from typing import Tuple
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pytest_mock import MockerFixture

from zenml.deployers.exceptions import (
    DeploymentNotFoundError,
    DeploymentTimeoutError,
)
from zenml.deployers.local.local_deployer import (
    LocalDeployer,
    LocalDeployerConfig,
)
from zenml.enums import DeploymentStatus, StackComponentType
from zenml.models import DeploymentOperationalState, DeploymentResponse


@pytest.fixture(scope="session", autouse=True)
def auto_environment() -> None:
    """Keep these polling-only tests independent of a configured ZenML store."""


@pytest.fixture(scope="module", autouse=True)
def check_module_requirements() -> None:
    """Polling tests have no deployment or integration requirements."""


class PollingDeployer(LocalDeployer):
    """Expose polling without provisioning local resources."""

    def poll(
        self,
        deployment: DeploymentResponse,
        desired_status: DeploymentStatus = DeploymentStatus.RUNNING,
        timeout: int = 30,
    ) -> Tuple[DeploymentResponse, DeploymentOperationalState]:
        """Poll a deployment using the shared lifecycle implementation.

        Args:
            deployment: Deployment to poll.
            desired_status: Status to wait for.
            timeout: Maximum wait in seconds.

        Returns:
            The updated deployment and its operational state.

        Raises:
            DeploymentTimeoutError: If the desired status is not reached.
        """
        return self._poll_deployment(deployment, desired_status, timeout)


@pytest.fixture
def polling_deployer(
    mocker: MockerFixture,
) -> Tuple[PollingDeployer, MagicMock, MagicMock]:
    """Create a deployer with isolated storage, clock, and logging boundaries.

    Args:
        mocker: Fixture for replacing external boundaries.

    Returns:
        The deployer, deployment, and captured logger.
    """
    deployer = PollingDeployer(
        name="test",
        id=uuid4(),
        config=LocalDeployerConfig(),
        flavor="local",
        type=StackComponentType.DEPLOYER,
        user=None,
        created=datetime.now(),
        updated=datetime.now(),
    )
    deployment = MagicMock(spec=DeploymentResponse)
    deployment.name = "test"
    deployment.id = uuid4()
    deployment.status = DeploymentStatus.PENDING

    def update(
        deployment: DeploymentResponse, state: DeploymentOperationalState
    ) -> DeploymentResponse:
        """Apply a backend state without accessing a ZenML store.

        Args:
            deployment: Deployment to update.
            state: State returned by the backend.

        Returns:
            The updated deployment.
        """
        deployment.status = state.status
        return deployment

    mocker.patch.object(deployer, "_update_deployment", side_effect=update)
    mocker.patch.object(
        deployer, "_check_deployment_health", return_value=True
    )
    clock = [0.0]
    mocker.patch(
        "zenml.deployers.base_deployer.time.time", side_effect=lambda: clock[0]
    )

    def advance(seconds: float) -> None:
        """Advance the test clock instead of sleeping.

        Args:
            seconds: Time to advance in seconds.
        """
        clock[0] += seconds

    mocker.patch(
        "zenml.deployers.base_deployer.time.sleep", side_effect=advance
    )
    logger = mocker.patch("zenml.deployers.base_deployer.logger")
    return deployer, deployment, logger


def test_polling_displays_elapsed_progress_until_ready(
    polling_deployer: Tuple[PollingDeployer, MagicMock, MagicMock],
    mocker: MockerFixture,
) -> None:
    """Show elapsed progress while pending and explain the startup state."""
    deployer, deployment, logger = polling_deployer
    mocker.patch.object(
        deployer,
        "do_get_deployment_state",
        side_effect=[
            DeploymentOperationalState(status=value)
            for value in (
                DeploymentStatus.PENDING,
                DeploymentStatus.PENDING,
                DeploymentStatus.RUNNING,
            )
        ],
    )

    result, state = deployer.poll(deployment)

    assert result.status == state.status == DeploymentStatus.RUNNING
    messages = [call.args[0] for call in logger.info.call_args_list]
    assert any("health checks" in message for message in messages)
    assert any(
        "pending" in message and "0 seconds" in message for message in messages
    )
    assert any(
        "pending" in message and "5 seconds" in message for message in messages
    )


def test_polling_timeout_has_diagnostic_commands(
    polling_deployer: Tuple[PollingDeployer, MagicMock, MagicMock],
    mocker: MockerFixture,
) -> None:
    """Give recovery guidance without deleting a still-starting deployment."""
    deployer, deployment, _ = polling_deployer
    mocker.patch.object(
        deployer,
        "do_get_deployment_state",
        return_value=DeploymentOperationalState(
            status=DeploymentStatus.PENDING
        ),
    )
    deprovision = mocker.patch.object(deployer, "do_deprovision_deployment")

    with pytest.raises(DeploymentTimeoutError) as exc:
        deployer.poll(deployment, timeout=1)

    message = str(exc.value)
    assert "pending" in message
    assert "may still" in message
    assert f"zenml deployment refresh {deployment.id}" in message
    assert f"zenml deployment logs {deployment.id}" in message
    deprovision.assert_not_called()


@pytest.mark.parametrize(
    "desired_status", [DeploymentStatus.RUNNING, DeploymentStatus.ABSENT]
)
def test_polling_stops_on_desired_status(
    polling_deployer: Tuple[PollingDeployer, MagicMock, MagicMock],
    mocker: MockerFixture,
    desired_status: DeploymentStatus,
) -> None:
    """Preserve terminal status handling for every lifecycle target."""
    deployer, deployment, _ = polling_deployer
    get_state = mocker.patch.object(
        deployer,
        "do_get_deployment_state",
        return_value=DeploymentOperationalState(status=desired_status),
    )

    result, state = deployer.poll(deployment, desired_status)

    assert result.status == state.status == desired_status
    get_state.assert_called_once()


def test_polling_stops_on_backend_error(
    polling_deployer: Tuple[PollingDeployer, MagicMock, MagicMock],
    mocker: MockerFixture,
) -> None:
    """Do not keep waiting or report success after a backend error."""
    deployer, deployment, _ = polling_deployer
    get_state = mocker.patch.object(
        deployer,
        "do_get_deployment_state",
        return_value=DeploymentOperationalState(status=DeploymentStatus.ERROR),
    )

    result, state = deployer.poll(deployment)

    assert result.status == state.status == DeploymentStatus.ERROR
    get_state.assert_called_once()


def test_polling_waits_for_health_checks(
    polling_deployer: Tuple[PollingDeployer, MagicMock, MagicMock],
    mocker: MockerFixture,
) -> None:
    """A running backend must pass health checks before reporting readiness."""
    deployer, deployment, logger = polling_deployer
    get_state = mocker.patch.object(
        deployer,
        "do_get_deployment_state",
        side_effect=[
            DeploymentOperationalState(status=DeploymentStatus.RUNNING),
            DeploymentOperationalState(status=DeploymentStatus.RUNNING),
        ],
    )
    mocker.patch.object(
        deployer, "_check_deployment_health", side_effect=[False, True]
    )

    result, state = deployer.poll(deployment)

    assert result.status == state.status == DeploymentStatus.RUNNING
    assert get_state.call_count == 2
    messages = [call.args[0] for call in logger.info.call_args_list]
    assert any("pending" in message for message in messages)
    assert "reached state 'running' after 5 seconds" in messages[-1]


def test_polling_missing_deployment_completes_deprovisioning(
    polling_deployer: Tuple[PollingDeployer, MagicMock, MagicMock],
    mocker: MockerFixture,
) -> None:
    """A deleted deployment still resolves to absent during shutdown."""
    deployer, deployment, _ = polling_deployer
    mocker.patch.object(
        deployer,
        "do_get_deployment_state",
        side_effect=DeploymentNotFoundError("deleted"),
    )

    result, state = deployer.poll(deployment, DeploymentStatus.ABSENT)

    assert result.status == state.status == DeploymentStatus.ABSENT
