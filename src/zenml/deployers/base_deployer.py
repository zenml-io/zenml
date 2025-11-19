#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Base class for all ZenML deployers."""

import secrets
import string
import time
from abc import ABC, abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generator,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)
from uuid import UUID

import requests

from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import track_handler
from zenml.client import Client
from zenml.config import DeploymentDefaultEndpoints
from zenml.config.base_settings import BaseSettings
from zenml.constants import (
    ENV_ZENML_ACTIVE_PROJECT_ID,
    ENV_ZENML_ACTIVE_STACK_ID,
)
from zenml.deployers.exceptions import (
    DeployerError,
    DeploymentAlreadyExistsError,
    DeploymentDeployerMismatchError,
    DeploymentDeprovisionError,
    DeploymentNotFoundError,
    DeploymentProvisionError,
    DeploymentSnapshotMismatchError,
    DeploymentTimeoutError,
)
from zenml.enums import DeploymentStatus, StackComponentType
from zenml.logger import get_logger
from zenml.models import (
    DeploymentOperationalState,
    DeploymentRequest,
    DeploymentResponse,
    DeploymentUpdate,
    PipelineSnapshotResponse,
)
from zenml.orchestrators.utils import get_config_environment_vars
from zenml.stack import StackComponent
from zenml.stack.flavor import Flavor
from zenml.stack.stack_component import StackComponentConfig
from zenml.utils.uuid_utils import is_valid_uuid

if TYPE_CHECKING:
    from zenml.stack import Stack

logger = get_logger(__name__)

DEFAULT_DEPLOYMENT_LCM_TIMEOUT = 600


class BaseDeployerSettings(BaseSettings):
    """Base settings for all deployers."""

    auth_key: Optional[str] = None
    generate_auth_key: bool = False
    lcm_timeout: int = DEFAULT_DEPLOYMENT_LCM_TIMEOUT


class BaseDeployerConfig(StackComponentConfig):
    """Base config for all deployers."""


class BaseDeployer(StackComponent, ABC):
    """Base class for all ZenML deployers.

    The deployer serves three major purposes:

    1. It contains all the stack related configuration attributes required to
    interact with the remote pipeline deployment tool, service or platform (e.g.
    hostnames, URLs, references to credentials, other client related
    configuration parameters).

    2. It implements the life-cycle management for deployments, including
    discovery, creation, deletion and updating.

    3. It acts as a ZenML deployment registry, where every pipeline
    deployment is stored as a database entity through the ZenML Client. This
    allows the deployer to keep track of all externally running pipeline
    deployments and to manage their lifecycle.
    """

    @property
    def config(self) -> BaseDeployerConfig:
        """Returns the `BaseDeployerConfig` config.

        Returns:
            The configuration.
        """
        return cast(BaseDeployerConfig, self._config)

    @classmethod
    def get_active_deployer(cls) -> "BaseDeployer":
        """Get the deployer registered in the active stack.

        Returns:
            The deployer registered in the active stack.

        Raises:
            TypeError: if a deployer is not part of the
                active stack.
        """
        client = Client()
        deployer = client.active_stack.deployer
        if not deployer or not isinstance(deployer, cls):
            raise TypeError(
                "The active stack needs to have a deployer "
                "component registered to be able to deploy pipelines. "
                "You can create a new stack with a deployer component "
                "or update your active stack to add this component, e.g.:\n\n"
                "  `zenml deployer register ...`\n"
                "  `zenml stack register <STACK-NAME> -D ...`\n"
                "  or:\n"
                "  `zenml stack update -D ...`\n\n"
            )

        return deployer

    def _update_deployment(
        self,
        deployment: DeploymentResponse,
        operational_state: DeploymentOperationalState,
    ) -> DeploymentResponse:
        """Update an existing deployment instance with the operational state.

        Args:
            deployment: The deployment to update.
            operational_state: The operational state of the deployment.

        Returns:
            The updated deployment.
        """
        client = Client()
        if operational_state.status == DeploymentStatus.ABSENT:
            # Erase the URL and metadata for absent deployments
            operational_state.url = ""
            operational_state.metadata = {}

        return client.zen_store.update_deployment(
            deployment.id,
            DeploymentUpdate.from_operational_state(operational_state),
        )

    def _check_deployment_inputs_outputs(
        self,
        snapshot: PipelineSnapshotResponse,
    ) -> None:
        """Check if the deployment has compiled schemas for the pipeline inputs and outputs.

        Args:
            snapshot: The pipeline snapshot to check.

        Raises:
            DeploymentProvisionError: if the deployment has no compiled schemas
                for the pipeline inputs and outputs.
        """
        if (
            not snapshot.pipeline_spec
            or not snapshot.pipeline_spec.input_schema
            or not snapshot.pipeline_spec.output_schema
        ):
            raise DeploymentProvisionError(
                f"The pipeline with name '{snapshot.pipeline.name}' referenced "
                f"by the deployment with name or ID "
                f"'{snapshot.name or snapshot.id}' "
                "is missing the compiled schemas for the pipeline inputs or "
                "outputs. This is most likely because some of the pipeline "
                "inputs or outputs are not JSON serializable. Please check that "
                "all the pipeline input arguments and return values have data "
                "types that are JSON serializable."
            )

    def _check_deployment_deployer(
        self,
        deployment: DeploymentResponse,
    ) -> None:
        """Check if the deployment is managed by this deployer.

        Args:
            deployment: The deployment to check.

        Raises:
            DeploymentDeployerMismatchError: if the deployment is
                not managed by this deployer.
        """
        if deployment.deployer_id and deployment.deployer_id != self.id:
            deployer = deployment.deployer
            assert deployer, "Deployer not found"
            raise DeploymentDeployerMismatchError(
                f"The deployment with name '{deployment.name}' was provisioned "
                f"with a deployer stack component ({deployer.name}) that is "
                f"different from the active one: {self.name}. "
                f"You can try one of the following:\n"
                f"1. Use a different name for the deployment\n"
                f"2. Delete the existing '{deployment.name}' deployment\n"
                f"3. Use a stack that contains the '{self.name}' deployer stack "
                "component\n"
            )

    def _check_deployment_snapshot(
        self, snapshot: Optional[PipelineSnapshotResponse] = None
    ) -> None:
        """Check if the snapshot was created for this deployer.

        Args:
            snapshot: The pipeline snapshot to check.

        Raises:
            DeploymentSnapshotMismatchError: if the pipeline snapshot is
                not built for this deployer.
        """
        if not snapshot:
            return

        if snapshot.stack and snapshot.stack.components.get(
            StackComponentType.DEPLOYER
        ):
            deployer = snapshot.stack.components[StackComponentType.DEPLOYER][
                0
            ]
            if deployer.id != self.id:
                raise DeploymentSnapshotMismatchError(
                    f"The pipeline snapshot with ID '{snapshot.id}' "
                    f"was not created for the deployer {self.name}. This will "
                    "lead to unexpected behavior and is not allowed."
                )

    def _check_snapshot_already_deployed(
        self,
        snapshot: PipelineSnapshotResponse,
        new_deployment_id_or_name: Union[str, UUID],
    ) -> None:
        """Check if the snapshot is already deployed to another deployment.

        Args:
            snapshot: The pipeline snapshot to check.
            new_deployment_id_or_name: The ID or name of the deployment that is
                being provisioned.

        Raises:
            DeploymentAlreadyExistsError: if the snapshot is already deployed to
                another deployment.
        """
        if snapshot.deployment and (
            isinstance(snapshot.deployment.id, UUID)
            and snapshot.deployment.id != new_deployment_id_or_name
            or (
                isinstance(snapshot.deployment.id, str)
                and snapshot.deployment.name != new_deployment_id_or_name
            )
        ):
            raise DeploymentAlreadyExistsError(
                f"The pipeline snapshot with name or ID "
                f"'{snapshot.name or snapshot.id}' "
                f"already has an associated deployment: "
                f"'{snapshot.deployment.name or snapshot.deployment.id}'. "
                "You can try one of the following:\n"
                "1. Delete the existing deployment before provisioning "
                f"a new one: 'zenml deployment delete "
                f"{snapshot.deployment.name or snapshot.deployment.id}'\n"
                "2. Update the existing deployment with the snapshot: 'zenml "
                f"pipeline snapshot deploy {snapshot.name or snapshot.id} "
                f"--deployment {snapshot.deployment.name or snapshot.deployment.id}'\n"
                "3. Create and deploy a different snapshot: 'zenml snapshot "
                "create ...'\n"
            )

    def _generate_auth_key(self, key_length: int = 32) -> str:
        """Generate an authentication key.

        Args:
            key_length: The length of the authentication key.

        Returns:
            The generated authentication key.
        """
        # Generate a secure random string with letters, digits and special chars
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(key_length))

    def _check_deployment_health(
        self,
        deployment: DeploymentResponse,
    ) -> bool:
        """Check if the deployment is healthy by calling its health check endpoint.

        Args:
            deployment: The deployment to check.

        Returns:
            True if the deployment is healthy, False otherwise.
        """
        assert deployment.snapshot, "Deployment snapshot not found"

        settings = (
            deployment.snapshot.pipeline_configuration.deployment_settings
        )

        # If the health check endpoint is disabled, we consider the deployment healthy.
        if (
            DeploymentDefaultEndpoints.HEALTH
            not in settings.include_default_endpoints
        ):
            return True

        if not deployment.url:
            return False

        health_check_path = f"{settings.root_url_path}{settings.api_url_path}{settings.health_url_path}"
        health_check_url = f"{deployment.url}{health_check_path}"

        # Attempt to connect to the deployment and check if it is healthy
        try:
            response = requests.get(health_check_url, timeout=3)
            if response.status_code == 200:
                return True
            else:
                logger.debug(
                    f"Health check endpoint for deployment '{deployment.name}' "
                    f"at '{health_check_url}' returned status code "
                    f"{response.status_code}"
                )
                return False
        except Exception as e:
            logger.debug(
                f"Health check endpoint for deployment '{deployment.name}' "
                f"at '{health_check_url}' is not reachable: {e}"
            )
            return False

    def _poll_deployment(
        self,
        deployment: DeploymentResponse,
        desired_status: DeploymentStatus,
        timeout: int,
    ) -> Tuple[DeploymentResponse, DeploymentOperationalState]:
        """Poll the deployment until it reaches the desired status, an error occurs or times out.

        Args:
            deployment: The deployment to poll.
            desired_status: The desired status of the deployment.
            timeout: The maximum time in seconds to wait for the pipeline
                deployment to reach the desired status.

        Returns:
            The updated deployment and the operational state of the
            deployment.

        Raises:
            DeploymentTimeoutError: if the deployment
                deployment times out while waiting to reach the desired status.
        """
        logger.info(
            f"Waiting for the deployment {deployment.name} to reach "
            f"desired state '{desired_status}' for max {timeout} seconds..."
        )

        start_time = time.time()
        sleep_time = 5
        while True:
            deployment_state = DeploymentOperationalState(
                status=DeploymentStatus.ERROR,
            )
            try:
                deployment_state = self.do_get_deployment_state(deployment)

                if deployment_state.status == DeploymentStatus.RUNNING:
                    if not self._check_deployment_health(deployment):
                        deployment_state.status = DeploymentStatus.PENDING

            except DeploymentNotFoundError:
                deployment_state = DeploymentOperationalState(
                    status=DeploymentStatus.ABSENT
                )
            except DeployerError as e:
                logger.exception(
                    f"Failed to get deployment {deployment.name}: {e}"
                )
            finally:
                deployment = self._update_deployment(
                    deployment, deployment_state
                )

            if deployment.status in [
                desired_status,
                DeploymentStatus.ERROR,
            ]:
                break

            elapsed_time = int(time.time() - start_time)
            if elapsed_time > timeout:
                raise DeploymentTimeoutError(
                    f"Timed out waiting for deployment {deployment.name} "
                    f"to reach desired state '{desired_status}' after {timeout} "
                    "seconds"
                )
            logger.debug(
                f"The deployment {deployment.name} state is still "
                f"'{deployment.status}' after {elapsed_time} seconds. Waiting for "
                f"max {timeout - elapsed_time} seconds..."
            )
            time.sleep(sleep_time)

        return deployment, deployment_state

    def _get_deployment_analytics_metadata(
        self,
        deployment: "DeploymentResponse",
        stack: Optional["Stack"] = None,
    ) -> Dict[str, Any]:
        """Returns the deployment metadata.

        Args:
            deployment: The deployment to track.
            stack: The stack on which the pipeline is deployed.

        Returns:
            the metadata about the deployment
        """
        snapshot = deployment.snapshot
        stack_metadata = {}
        if stack:
            stack_metadata = {
                component_type.value: component.flavor
                for component_type, component in stack.components.items()
            }
        return {
            "project_id": deployment.project_id,
            "store_type": Client().zen_store.type.value,
            **stack_metadata,
            "deployment_id": str(deployment.id),
            "snapshot_id": str(snapshot.id) if snapshot else None,
            "deployer_id": str(self.id),
            "deployer_flavor": self.flavor,
            "deployment_status": deployment.status,
        }

    def provision_deployment(
        self,
        snapshot: PipelineSnapshotResponse,
        stack: "Stack",
        deployment_name_or_id: Union[str, UUID],
        replace: bool = True,
        timeout: Optional[int] = None,
    ) -> DeploymentResponse:
        """Provision a deployment.

        The provision_deployment method is the main entry point for
        provisioning deployments using the deployer. It is used to deploy
        a pipeline snapshot as an HTTP deployment, or update an existing
        deployment instance with the same name. The method returns a
        DeploymentResponse object that is a representation of the
        external deployment instance.

        Args:
            snapshot: The pipeline snapshot to deploy as an HTTP deployment.
            stack: The stack the pipeline will be deployed on.
            deployment_name_or_id: Unique name or ID for the deployment.
                This name must be unique at the project level.
            replace: If True, it will update in-place any existing pipeline
                deployment instance with the same name. If False, and the pipeline
                deployment instance already exists, it will raise a
                DeploymentAlreadyExistsError.
            timeout: The maximum time in seconds to wait for the pipeline
                deployment to be provisioned. If provided, will override the
                deployer's default timeout.

        Raises:
            DeploymentAlreadyExistsError: if the deployment already
                exists and replace is False.
            DeploymentProvisionError: if the deployment fails.
            DeploymentSnapshotMismatchError: if the pipeline snapshot
                was not created for this deployer.
            DeploymentNotFoundError: if the deployment with the
                given ID is not found.
            DeployerError: if an unexpected error occurs.

        Returns:
            The DeploymentResponse object representing the provisioned
            deployment.
        """
        if not replace and is_valid_uuid(deployment_name_or_id):
            raise DeploymentAlreadyExistsError(
                f"A deployment with ID '{deployment_name_or_id}' "
                "already exists"
            )

        self._check_deployment_inputs_outputs(snapshot)

        client = Client()

        settings = cast(
            BaseDeployerSettings,
            self.get_settings(snapshot),
        )

        timeout = timeout or settings.lcm_timeout
        auth_key = settings.auth_key
        if not auth_key and settings.generate_auth_key:
            auth_key = self._generate_auth_key()

        if snapshot.stack and snapshot.stack.id != stack.id:
            # When a different stack is used then the one the snapshot was
            # created for, the container image may not have the correct
            # dependencies installed, which leads to unexpected errors during
            # deployment. To avoid this, we raise an error here.
            raise DeploymentSnapshotMismatchError(
                f"The pipeline snapshot with ID '{snapshot.id}' "
                f"was not created for the stack {stack.name} and might not "
                "have the correct dependencies installed. This may "
                "lead to unexpected behavior during deployment. Please switch "
                f"to the correct active stack '{snapshot.stack.name}' or use "
                "a different snapshot."
            )

        try:
            # Get the existing deployment
            deployment = client.get_deployment(
                deployment_name_or_id, project=snapshot.project_id
            )

            self._check_snapshot_already_deployed(snapshot, deployment.id)

            logger.debug(
                f"Existing deployment found with name '{deployment.name}'"
            )
        except KeyError:
            if isinstance(deployment_name_or_id, UUID):
                raise DeploymentNotFoundError(
                    f"Deployment with ID '{deployment_name_or_id}' not found"
                )

            self._check_snapshot_already_deployed(
                snapshot, deployment_name_or_id
            )

            logger.debug(
                f"Creating new deployment {deployment_name_or_id} with "
                f"snapshot ID: {snapshot.id}"
            )

            # Create the deployment request
            deployment_request = DeploymentRequest(
                name=deployment_name_or_id,
                project=snapshot.project_id,
                snapshot_id=snapshot.id,
                deployer_id=self.id,  # This deployer's ID
                auth_key=auth_key,
            )

            deployment = client.zen_store.create_deployment(deployment_request)
            logger.debug(
                f"Created new deployment with name '{deployment.name}' "
                f"and ID: {deployment.id}"
            )
        else:
            if not replace:
                raise DeploymentAlreadyExistsError(
                    f"A deployment with name '{deployment.name}' "
                    "already exists"
                )

            self._check_deployment_deployer(deployment)
            self._check_deployment_snapshot(snapshot)

            deployment_update = DeploymentUpdate(
                snapshot_id=snapshot.id,
            )
            if (
                deployment.auth_key
                and not auth_key
                or not deployment.auth_key
                and auth_key
            ):
                # Key was either added or removed
                deployment_update.auth_key = auth_key
            elif deployment.auth_key != auth_key and (
                settings.auth_key or not settings.generate_auth_key
            ):
                # Key was changed and not because of re-generation
                deployment_update.auth_key = auth_key

            # The deployment has been updated
            deployment = client.zen_store.update_deployment(
                deployment.id,
                deployment_update,
            )

        logger.info(
            f"Provisioning deployment {deployment.name} with "
            f"snapshot ID: {snapshot.id}"
        )

        environment, secrets = get_config_environment_vars(
            deployment_id=deployment.id,
        )

        # Make sure to use the correct active stack/project which correspond
        # to the supplied stack and snapshot, which may be different from the
        # active stack/project
        environment[ENV_ZENML_ACTIVE_STACK_ID] = str(stack.id)
        environment[ENV_ZENML_ACTIVE_PROJECT_ID] = str(snapshot.project_id)

        start_time = time.time()
        deployment_state = DeploymentOperationalState(
            status=DeploymentStatus.ERROR,
        )
        with track_handler(
            AnalyticsEvent.DEPLOY_PIPELINE
        ) as analytics_handler:
            try:
                deployment_state = self.do_provision_deployment(
                    deployment,
                    stack=stack,
                    environment=environment,
                    secrets=secrets,
                    timeout=timeout,
                )
            except DeploymentProvisionError as e:
                raise DeploymentProvisionError(
                    f"Failed to provision deployment {deployment.name}: {e}"
                ) from e
            except DeployerError as e:
                raise DeployerError(
                    f"Failed to provision deployment {deployment.name}: {e}"
                ) from e
            except Exception as e:
                raise DeployerError(
                    f"Unexpected error while provisioning deployment for "
                    f"{deployment.name}: {e}"
                ) from e
            finally:
                deployment = self._update_deployment(
                    deployment, deployment_state
                )

            logger.info(
                f"Provisioned deployment {deployment.name} with "
                f"snapshot ID: {snapshot.id}. Operational state is: "
                f"{deployment_state.status}"
            )

            try:
                if deployment_state.status == DeploymentStatus.RUNNING:
                    return deployment

                # Subtract the time spent deploying the deployment from the
                # timeout
                timeout = timeout - int(time.time() - start_time)
                deployment, _ = self._poll_deployment(
                    deployment, DeploymentStatus.RUNNING, timeout
                )

                if deployment.status != DeploymentStatus.RUNNING:
                    raise DeploymentProvisionError(
                        f"Failed to provision deployment {deployment.name}: "
                        f"The deployment's operational state is "
                        f"{deployment.status}. Please check the status or logs "
                        "of the deployment for more information."
                    )

            finally:
                analytics_handler.metadata = (
                    self._get_deployment_analytics_metadata(
                        deployment=deployment,
                        stack=stack,
                    )
                )

            return deployment

    def refresh_deployment(
        self,
        deployment_name_or_id: Union[str, UUID],
        project: Optional[UUID] = None,
    ) -> DeploymentResponse:
        """Refresh the status of a deployment by name or ID.

        Call this to refresh the operational state of a deployment.

        Args:
            deployment_name_or_id: The name or ID of the deployment to get.
            project: The project ID of the deployment to get. Required
                if a name is provided.

        Returns:
            The deployment.

        Raises:
            DeploymentNotFoundError: if the deployment is not found.
            DeployerError: if an unexpected error occurs.
        """
        client = Client()
        try:
            deployment = client.get_deployment(
                deployment_name_or_id, project=project
            )
        except KeyError:
            raise DeploymentNotFoundError(
                f"Deployment with name or ID '{deployment_name_or_id}' "
                f"not found"
            )

        self._check_deployment_deployer(deployment)

        deployment_state = DeploymentOperationalState(
            status=DeploymentStatus.ERROR,
        )
        try:
            deployment_state = self.do_get_deployment_state(deployment)
            if deployment_state.status == DeploymentStatus.RUNNING:
                if not self._check_deployment_health(deployment):
                    deployment_state.status = DeploymentStatus.PENDING
        except DeploymentNotFoundError:
            deployment_state.status = DeploymentStatus.ABSENT
        except DeployerError as e:
            raise DeployerError(
                f"Failed to refresh deployment {deployment_name_or_id}: {e}"
            ) from e
        except Exception as e:
            raise DeployerError(
                f"Unexpected error while refreshing deployment for "
                f"{deployment_name_or_id}: {e}"
            ) from e
        finally:
            deployment = self._update_deployment(deployment, deployment_state)

        return deployment

    def deprovision_deployment(
        self,
        deployment_name_or_id: Union[str, UUID],
        project: Optional[UUID] = None,
        timeout: Optional[int] = None,
    ) -> DeploymentResponse:
        """Deprovision a deployment.

        Args:
            deployment_name_or_id: The name or ID of the deployment to
                deprovision.
            project: The project ID of the deployment to deprovision.
                Required if a name is provided.
            timeout: The maximum time in seconds to wait for the pipeline
                deployment to deprovision. If provided, will override the
                deployer's default timeout.

        Returns:
            The deployment.

        Raises:
            DeploymentNotFoundError: if the deployment is not found
                or is not managed by this deployer.
            DeploymentDeprovisionError: if the deployment
                deprovision fails.
            DeployerError: if an unexpected error occurs.
        """
        client = Client()
        try:
            deployment = client.get_deployment(
                deployment_name_or_id, project=project
            )
        except KeyError:
            raise DeploymentNotFoundError(
                f"Deployment with name or ID '{deployment_name_or_id}' "
                f"not found"
            )

        self._check_deployment_deployer(deployment)

        if not timeout and deployment.snapshot:
            settings = cast(
                BaseDeployerSettings,
                self.get_settings(deployment.snapshot),
            )

            timeout = settings.lcm_timeout

        timeout = timeout or DEFAULT_DEPLOYMENT_LCM_TIMEOUT

        start_time = time.time()
        deployment_state = DeploymentOperationalState(
            status=DeploymentStatus.ERROR,
        )
        with track_handler(
            AnalyticsEvent.STOP_DEPLOYMENT
        ) as analytics_handler:
            try:
                deleted_deployment_state = self.do_deprovision_deployment(
                    deployment, timeout
                )
                if not deleted_deployment_state:
                    # When do_delete_deployment returns a None value, this
                    # is to signal that the deployment is already fully deprovisioned.
                    deployment_state.status = DeploymentStatus.ABSENT
            except DeploymentNotFoundError:
                deployment_state.status = DeploymentStatus.ABSENT
            except DeployerError as e:
                raise DeployerError(
                    f"Failed to delete deployment {deployment_name_or_id}: {e}"
                ) from e
            except Exception as e:
                raise DeployerError(
                    f"Unexpected error while deleting deployment for "
                    f"{deployment_name_or_id}: {e}"
                ) from e
            finally:
                deployment = self._update_deployment(
                    deployment, deployment_state
                )

            try:
                if deployment_state.status == DeploymentStatus.ABSENT:
                    return deployment

                # Subtract the time spent deprovisioning the deployment from the timeout
                timeout = timeout - int(time.time() - start_time)
                deployment, _ = self._poll_deployment(
                    deployment, DeploymentStatus.ABSENT, timeout
                )

                if deployment.status != DeploymentStatus.ABSENT:
                    raise DeploymentDeprovisionError(
                        f"Failed to deprovision deployment {deployment_name_or_id}: "
                        f"Operational state: {deployment.status}"
                    )

            finally:
                analytics_handler.metadata = (
                    self._get_deployment_analytics_metadata(
                        deployment=deployment,
                        stack=None,
                    )
                )

            return deployment

    def delete_deployment(
        self,
        deployment_name_or_id: Union[str, UUID],
        project: Optional[UUID] = None,
        force: bool = False,
        timeout: Optional[int] = None,
    ) -> None:
        """Deprovision and delete a deployment.

        Args:
            deployment_name_or_id: The name or ID of the deployment to
                delete.
            project: The project ID of the deployment to deprovision.
                Required if a name is provided.
            force: if True, force the deployment to delete even if it
                cannot be deprovisioned.
            timeout: The maximum time in seconds to wait for the pipeline
                deployment to be deprovisioned. If provided, will override the
                deployer's default timeout.

        Raises:
            DeployerError: if an unexpected error occurs.
        """
        client = Client()
        try:
            deployment = self.deprovision_deployment(
                deployment_name_or_id, project, timeout
            )
        except DeploymentNotFoundError:
            # The deployment was already deleted
            return
        except DeployerError as e:
            if force:
                logger.warning(
                    f"Failed to deprovision deployment "
                    f"{deployment_name_or_id}: {e}. Forcing deletion."
                )
                deployment = client.get_deployment(
                    deployment_name_or_id, project=project
                )
                client.zen_store.delete_deployment(deployment_id=deployment.id)
            else:
                raise
        else:
            client.zen_store.delete_deployment(deployment_id=deployment.id)

    def get_deployment_logs(
        self,
        deployment_name_or_id: Union[str, UUID],
        project: Optional[UUID] = None,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Get the logs of a deployment.

        Args:
            deployment_name_or_id: The name or ID of the deployment to get
                the logs of.
            project: The project ID of the deployment to get the logs of.
                Required if a name is provided.
            follow: if True, the logs will be streamed as they are written.
            tail: only retrieve the last NUM lines of log output.

        Returns:
            A generator that yields the logs of the deployment.

        Raises:
            DeploymentNotFoundError: if the deployment is not found.
            DeployerError: if an unexpected error occurs.
        """
        client = Client()
        try:
            deployment = client.get_deployment(
                deployment_name_or_id, project=project
            )
        except KeyError:
            raise DeploymentNotFoundError(
                f"Deployment with name or ID '{deployment_name_or_id}' "
                f"not found"
            )

        self._check_deployment_deployer(deployment)

        try:
            return self.do_get_deployment_state_logs(deployment, follow, tail)
        except DeployerError as e:
            raise DeployerError(
                f"Failed to get logs for deployment {deployment_name_or_id}: {e}"
            ) from e
        except Exception as e:
            raise DeployerError(
                f"Unexpected error while getting logs for deployment for "
                f"{deployment_name_or_id}: {e}"
            ) from e

    # ------------------ Abstract Methods ------------------

    @abstractmethod
    def do_provision_deployment(
        self,
        deployment: DeploymentResponse,
        stack: "Stack",
        environment: Dict[str, str],
        secrets: Dict[str, str],
        timeout: int,
    ) -> DeploymentOperationalState:
        """Abstract method to deploy a pipeline as an HTTP deployment.

        Concrete deployer subclasses must implement the following
        functionality in this method:

        - Create the actual deployment infrastructure (e.g.,
        FastAPI server, Kubernetes deployment, cloud function, etc.) based on
        the information in the deployment response, particularly the
        pipeline snapshot. When determining how to name the external
        resources, do not rely on the deployment name as being immutable
        or unique.

        - If the deployment infrastructure is already provisioned, update
        it to match the information in the deployment response.

        - Return a DeploymentOperationalState representing the operational
        state of the provisioned deployment.

        Note that the deployment infrastructure is not required to be
        deployed immediately. The deployer can return a
        DeploymentOperationalState with a status of
        DeploymentStatus.PENDING, and the base deployer will poll
        the deployment infrastructure by calling the
        `do_get_deployment_state` method until it is ready or it times out.

        Args:
            deployment: The deployment to deploy as an HTTP deployment.
            stack: The stack the pipeline will be deployed on.
            environment: A dictionary of environment variables to set on the
                deployment.
            secrets: A dictionary of secret environment variables to set
                on the deployment. These secret environment variables
                should not be exposed as regular environment variables on the
                deployer.
            timeout: The maximum time in seconds to wait for the pipeline
                deployment to be provisioned.

        Returns:
            The DeploymentOperationalState object representing the
            operational state of the provisioned deployment.

        Raises:
            DeploymentProvisionError: if provisioning the deployment
                fails.
            DeployerError: if an unexpected error occurs.
        """

    @abstractmethod
    def do_get_deployment_state(
        self,
        deployment: DeploymentResponse,
    ) -> DeploymentOperationalState:
        """Abstract method to get information about a deployment.

        Args:
            deployment: The deployment to get information about.

        Returns:
            The DeploymentOperationalState object representing the
            updated operational state of the deployment.

        Raises:
            DeploymentNotFoundError: if no deployment is found
                corresponding to the provided DeploymentResponse.
            DeployerError: if the deployment information cannot
                be retrieved for any other reason or if an unexpected error
                occurs.
        """

    @abstractmethod
    def do_get_deployment_state_logs(
        self,
        deployment: DeploymentResponse,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Abstract method to get the logs of a deployment.

        Args:
            deployment: The deployment to get the logs of.
            follow: if True, the logs will be streamed as they are written
            tail: only retrieve the last NUM lines of log output.

        Yields:
            The logs of the deployment.

        Raises:
            DeploymentNotFoundError: if no deployment is found
                corresponding to the provided DeploymentResponse.
            DeploymentLogsNotFoundError: if the deployment logs are not
                found.
            DeployerError: if the deployment logs cannot
                be retrieved for any other reason or if an unexpected error
                occurs.
        """

    @abstractmethod
    def do_deprovision_deployment(
        self,
        deployment: DeploymentResponse,
        timeout: int,
    ) -> Optional[DeploymentOperationalState]:
        """Abstract method to deprovision a deployment.

        Concrete deployer subclasses must implement the following
        functionality in this method:

        - Deprovision the actual deployment infrastructure (e.g.,
        FastAPI server, Kubernetes deployment, cloud function, etc.) based on
        the information in the deployment response.

        - Return a DeploymentOperationalState representing the operational
        state of the deleted deployment, or None if the deletion is
        completed before the call returns.

        Note that the deployment infrastructure is not required to be
        deleted immediately. The deployer can return a
        DeploymentOperationalState with a status of
        DeploymentStatus.PENDING, and the base deployer will poll
        the deployment infrastructure by calling the
        `do_get_deployment_state` method until it is deleted or it times out.

        Args:
            deployment: The deployment to delete.
            timeout: The maximum time in seconds to wait for the pipeline
                deployment to be deprovisioned.

        Returns:
            The DeploymentOperationalState object representing the
            operational state of the deprovisioned deployment, or None
            if the deprovision is completed before the call returns.

        Raises:
            DeploymentNotFoundError: if no deployment is found
                corresponding to the provided DeploymentResponse.
            DeploymentDeprovisionError: if the deployment
                deprovision fails.
            DeployerError: if an unexpected error occurs.
        """


class BaseDeployerFlavor(Flavor):
    """Base class for deployer flavors."""

    @property
    def type(self) -> StackComponentType:
        """Returns the flavor type.

        Returns:
            The flavor type.
        """
        return StackComponentType.DEPLOYER

    @property
    def config_class(self) -> Type[BaseDeployerConfig]:
        """Returns `BaseDeployerConfig` config class.

        Returns:
                The config class.
        """
        return BaseDeployerConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type[BaseDeployer]:
        """The class that implements the deployer."""
