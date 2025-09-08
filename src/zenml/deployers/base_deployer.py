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
    Dict,
    Generator,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)
from uuid import UUID

from zenml.client import Client
from zenml.config.base_settings import BaseSettings
from zenml.constants import (
    ENV_ZENML_ACTIVE_PROJECT_ID,
    ENV_ZENML_ACTIVE_STACK_ID,
)
from zenml.deployers.exceptions import (
    DeployerError,
    PipelineEndpointAlreadyExistsError,
    PipelineEndpointDeployerMismatchError,
    PipelineEndpointDeploymentError,
    PipelineEndpointDeploymentMismatchError,
    PipelineEndpointDeploymentTimeoutError,
    PipelineEndpointDeprovisionError,
    PipelineEndpointNotFoundError,
)
from zenml.enums import PipelineEndpointStatus, StackComponentType
from zenml.logger import get_logger
from zenml.models import (
    PipelineDeploymentResponse,
    PipelineEndpointOperationalState,
    PipelineEndpointRequest,
    PipelineEndpointResponse,
    PipelineEndpointUpdate,
)
from zenml.orchestrators.utils import get_config_environment_vars
from zenml.stack import StackComponent
from zenml.stack.flavor import Flavor
from zenml.stack.stack_component import StackComponentConfig

if TYPE_CHECKING:
    from zenml.stack import Stack

logger = get_logger(__name__)

DEFAULT_PIPELINE_ENDPOINT_LCM_TIMEOUT = 600


class BaseDeployerSettings(BaseSettings):
    """Base settings for all deployers."""

    auth_key: Optional[str] = None
    generate_auth_key: bool = False
    lcm_timeout: int = DEFAULT_PIPELINE_ENDPOINT_LCM_TIMEOUT


class BaseDeployerConfig(StackComponentConfig):
    """Base config for all deployers."""


class BaseDeployer(StackComponent, ABC):
    """Base class for all ZenML deployers.

    The deployer serves three major purposes:

    1. It contains all the stack related configuration attributes required to
    interact with the remote pipeline serving tool, service or platform (e.g.
    hostnames, URLs, references to credentials, other client related
    configuration parameters).

    2. It implements the life-cycle management for pipeline endpoints, including
    discovery, creation, deletion and updating.

    3. It acts as a ZenML pipeline endpoint registry, where every pipeline
    endpoint is stored as a database entity through the ZenML Client. This
    allows the deployer to keep track of all externally running pipeline
    endpoints and to manage their lifecycle.
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
                "The active stack needs to have a pipeline "
                "server component registered to be able to deploy pipelines. "
                "You can create a new stack with a deployer component "
                "or update your active stack to add this component, e.g.:\n\n"
                "  `zenml deployer register ...`\n"
                "  `zenml stack register <STACK-NAME> -D ...`\n"
                "  or:\n"
                "  `zenml stack update -D ...`\n\n"
            )

        return deployer

    def _update_pipeline_endpoint(
        self,
        endpoint: PipelineEndpointResponse,
        operational_state: PipelineEndpointOperationalState,
    ) -> PipelineEndpointResponse:
        """Update an existing pipeline endpoint instance with the operational state.

        Args:
            endpoint: The pipeline endpoint to update.
            operational_state: The operational state of the pipeline endpoint.

        Returns:
            The updated pipeline endpoint.
        """
        client = Client()
        if operational_state.status == PipelineEndpointStatus.ABSENT:
            # Erase the URL and metadata for absent endpoints
            operational_state.url = ""
            operational_state.metadata = {}

        return client.zen_store.update_pipeline_endpoint(
            endpoint.id,
            PipelineEndpointUpdate.from_operational_state(operational_state),
        )

    def _check_pipeline_endpoint_deployer(
        self,
        endpoint: PipelineEndpointResponse,
    ) -> None:
        """Check if the pipeline endpoint is managed by this deployer.

        Args:
            endpoint: The pipeline endpoint to check.

        Raises:
            PipelineEndpointDeployerMismatchError: if the pipeline endpoint is
                not managed by this deployer.
        """
        if endpoint.deployer_id and endpoint.deployer_id != self.id:
            deployer = endpoint.deployer
            assert deployer, "Deployer not found"
            raise PipelineEndpointDeployerMismatchError(
                f"The existing pipeline endpoint with name '{endpoint.name}' "
                f"in project {endpoint.project_id} is not managed by the "
                f"active deployer stack component '{deployer.name}'. "
                "Please switch to the correct deployer in your stack "
                f"'{self.name}' and try again or use a different endpoint name."
            )

    def _check_pipeline_endpoint_deployment(
        self, deployment: Optional[PipelineDeploymentResponse] = None
    ) -> None:
        """Check if the deployment was created for this deployer.

        Args:
            deployment: The pipeline deployment to check.

        Raises:
            PipelineEndpointDeployerMismatchError: if the pipeline deployment is
                not built for this deployer.
        """
        if not deployment:
            return

        if deployment.stack and deployment.stack.components.get(
            StackComponentType.DEPLOYER
        ):
            deployer = deployment.stack.components[
                StackComponentType.DEPLOYER
            ][0]
            if deployer.id != self.id:
                raise PipelineEndpointDeploymentMismatchError(
                    f"The pipeline deployment with ID '{deployment.id}' "
                    f"was not created for the deployer {self.name}. This will "
                    "lead to unexpected behavior and is not allowed."
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

    def _poll_pipeline_endpoint(
        self,
        endpoint: PipelineEndpointResponse,
        desired_status: PipelineEndpointStatus,
        timeout: int,
    ) -> Tuple[PipelineEndpointResponse, PipelineEndpointOperationalState]:
        """Poll the pipeline endpoint until it reaches the desired status, an error occurs or times out.

        Args:
            endpoint: The pipeline endpoint to poll.
            desired_status: The desired status of the pipeline endpoint.
            timeout: The maximum time in seconds to wait for the pipeline
                endpoint to reach the desired status.

        Returns:
            The updated pipeline endpoint and the operational state of the
            pipeline endpoint.

        Raises:
            PipelineEndpointDeploymentTimeoutError: if the pipeline endpoint
                deployment times out while waiting to reach the desired status.
        """
        start_time = time.time()
        sleep_time = 5
        while True:
            endpoint_state = PipelineEndpointOperationalState(
                status=PipelineEndpointStatus.ERROR,
            )
            try:
                endpoint_state = self.do_get_pipeline_endpoint(endpoint)
            except PipelineEndpointNotFoundError:
                endpoint_state = PipelineEndpointOperationalState(
                    status=PipelineEndpointStatus.ABSENT
                )
            except DeployerError as e:
                logger.exception(
                    f"Failed to get pipeline endpoint {endpoint.name}: {e}"
                )
            finally:
                endpoint = self._update_pipeline_endpoint(
                    endpoint, endpoint_state
                )

            if endpoint.status in [
                desired_status,
                PipelineEndpointStatus.ERROR,
            ]:
                break

            elapsed_time = int(time.time() - start_time)
            if elapsed_time > timeout:
                raise PipelineEndpointDeploymentTimeoutError(
                    f"Timed out waiting for pipeline endpoint {endpoint.name} "
                    f"to reach desired state '{desired_status}' after {timeout} "
                    "seconds"
                )
            logger.info(
                f"The pipeline endpoint {endpoint.name} state is still "
                f"'{endpoint.status}' after {elapsed_time} seconds. Waiting for "
                f"max {timeout - elapsed_time} seconds..."
            )
            time.sleep(sleep_time)

        return endpoint, endpoint_state

    def provision_pipeline_endpoint(
        self,
        deployment: PipelineDeploymentResponse,
        stack: "Stack",
        endpoint_name_or_id: Union[str, UUID],
        replace: bool = True,
        timeout: Optional[int] = None,
    ) -> PipelineEndpointResponse:
        """Provision a pipeline endpoint.

        The provision_pipeline_endpoint method is the main entry point for
        provisioning pipeline endpoints using the deployer. It is used to serve
        a pipeline deployment as an HTTP endpoint, or update an existing
        pipeline endpoint instance with the same name. The method returns a
        PipelineEndpointResponse object that is a representation of the
        external pipeline endpoint instance.

        Args:
            deployment: The pipeline deployment to serve as an HTTP endpoint.
            stack: The stack the pipeline will be served on.
            endpoint_name_or_id: Unique name or ID for the pipeline endpoint.
                This name must be unique at the project level.
            replace: If True, it will update in-place any existing pipeline
                endpoint instance with the same name. If False, and the pipeline
                endpoint instance already exists, it will raise a
                PipelineEndpointAlreadyExistsError.
            timeout: The maximum time in seconds to wait for the pipeline
                endpoint to be provisioned. If provided, will override the
                deployer's default timeout.

        Raises:
            PipelineEndpointAlreadyExistsError: if the pipeline endpoint already
                exists and replace is False.
            PipelineEndpointDeploymentError: if the pipeline deployment fails.
            DeployerError: if an unexpected error occurs.

        Returns:
            The PipelineEndpointResponse object representing the deployed
            pipeline endpoint.
        """
        client = Client()

        settings = cast(
            BaseDeployerSettings,
            self.get_settings(deployment),
        )

        timeout = timeout or settings.lcm_timeout
        auth_key = settings.auth_key
        if not auth_key and settings.generate_auth_key:
            auth_key = self._generate_auth_key()

        if deployment.stack and deployment.stack.id != stack.id:
            # When a different stack is used then the one the deployment was
            # created for, the container image may not have the correct
            # dependencies installed, which leads to unexpected errors during
            # deployment. To avoid this, we raise an error here.
            raise PipelineEndpointDeploymentMismatchError(
                f"The pipeline deployment with ID '{deployment.id}' "
                f"was not created for the stack {stack.name} and might not "
                "have the correct dependencies installed. This may "
                "lead to unexpected behavior during deployment. Please switch "
                f"to the correct active stack '{deployment.stack.name}' or use "
                "a different deployment."
            )

        try:
            # Get the existing pipeline endpoint
            endpoint = client.get_pipeline_endpoint(
                endpoint_name_or_id, project=deployment.project_id
            )

            logger.debug(
                f"Existing pipeline endpoint found with name '{endpoint.name}'"
            )
        except KeyError:
            if isinstance(endpoint_name_or_id, UUID):
                raise

            logger.debug(
                f"Creating new pipeline endpoint {endpoint_name_or_id} with "
                f"deployment ID: {deployment.id}"
            )

            # Create the pipeline endpoint request
            endpoint_request = PipelineEndpointRequest(
                name=endpoint_name_or_id,
                project=deployment.project_id,
                pipeline_deployment_id=deployment.id,
                deployer_id=self.id,  # This deployer's ID
                auth_key=auth_key,
            )

            endpoint = client.zen_store.create_pipeline_endpoint(
                endpoint_request
            )
            logger.debug(
                f"Created new pipeline endpoint with name '{endpoint.name}' "
                f"and ID: {endpoint.id}"
            )
        else:
            if not replace:
                raise PipelineEndpointAlreadyExistsError(
                    f"A pipeline endpoint with name '{endpoint.name}' "
                    "already exists"
                )

            self._check_pipeline_endpoint_deployer(endpoint)
            self._check_pipeline_endpoint_deployment(deployment)

            endpoint_update = PipelineEndpointUpdate(
                pipeline_deployment_id=deployment.id,
            )
            if (
                endpoint.auth_key
                and not auth_key
                or not endpoint.auth_key
                and auth_key
            ):
                # Key was either added or removed
                endpoint_update.auth_key = auth_key
            elif endpoint.auth_key != auth_key and (
                settings.auth_key or not settings.generate_auth_key
            ):
                # Key was changed and not because of re-generation
                endpoint_update.auth_key = auth_key

            # The deployment has been updated
            endpoint = client.zen_store.update_pipeline_endpoint(
                endpoint.id,
                endpoint_update,
            )

        logger.debug(
            f"Deploying pipeline endpoint {endpoint.name} with "
            f"deployment ID: {deployment.id}"
        )

        environment, secrets = get_config_environment_vars(
            deployment_id=endpoint.id,
        )

        # Make sure to use the correct active stack/project which correspond
        # to the supplied stack and deployment, which may be different from the
        # active stack/project
        environment[ENV_ZENML_ACTIVE_STACK_ID] = str(stack.id)
        environment[ENV_ZENML_ACTIVE_PROJECT_ID] = str(deployment.project_id)

        start_time = time.time()
        endpoint_state = PipelineEndpointOperationalState(
            status=PipelineEndpointStatus.ERROR,
        )
        try:
            endpoint_state = self.do_provision_pipeline_endpoint(
                endpoint,
                stack=stack,
                environment=environment,
                secrets=secrets,
                timeout=timeout,
            )
            endpoint = self._update_pipeline_endpoint(endpoint, endpoint_state)
        except PipelineEndpointDeploymentError as e:
            raise PipelineEndpointDeploymentError(
                f"Failed to deploy pipeline endpoint {endpoint.name}: {e}"
            ) from e
        except DeployerError as e:
            raise DeployerError(
                f"Failed to deploy pipeline endpoint {endpoint.name}: {e}"
            ) from e
        except Exception as e:
            raise DeployerError(
                f"Unexpected error while deploying pipeline endpoint for "
                f"{endpoint.name}: {e}"
            ) from e
        finally:
            endpoint = self._update_pipeline_endpoint(endpoint, endpoint_state)

        logger.debug(
            f"Deployed pipeline endpoint {endpoint.name} with "
            f"deployment ID: {deployment.id}. Operational state: "
            f"{endpoint_state.status}"
        )

        if endpoint_state.status == PipelineEndpointStatus.RUNNING:
            return endpoint

        # Subtract the time spent deploying the endpoint from the timeout
        timeout = timeout - int(time.time() - start_time)
        endpoint, _ = self._poll_pipeline_endpoint(
            endpoint, PipelineEndpointStatus.RUNNING, timeout
        )

        if endpoint.status != PipelineEndpointStatus.RUNNING:
            raise PipelineEndpointDeploymentError(
                f"Failed to deploy pipeline endpoint {endpoint.name}: "
                f"The endpoint's operational state is {endpoint.status}. "
                "Please check the status or logs of the endpoint for more "
                "information."
            )

        return endpoint

    def refresh_pipeline_endpoint(
        self,
        endpoint_name_or_id: Union[str, UUID],
        project: Optional[UUID] = None,
    ) -> PipelineEndpointResponse:
        """Refresh the status of a pipeline endpoint by name or ID.

        Call this to refresh the operational state of a pipeline endpoint.

        Args:
            endpoint_name_or_id: The name or ID of the pipeline endpoint to get.
            project: The project ID of the pipeline endpoint to get. Required
                if a name is provided.

        Returns:
            The pipeline endpoint.

        Raises:
            PipelineEndpointNotFoundError: if the pipeline endpoint is not found.
            DeployerError: if an unexpected error occurs.
        """
        client = Client()
        try:
            endpoint = client.get_pipeline_endpoint(
                endpoint_name_or_id, project=project
            )
        except KeyError:
            raise PipelineEndpointNotFoundError(
                f"Pipeline endpoint with name or ID '{endpoint_name_or_id}' "
                f"not found"
            )

        self._check_pipeline_endpoint_deployer(endpoint)

        endpoint_state = PipelineEndpointOperationalState(
            status=PipelineEndpointStatus.ERROR,
        )
        try:
            endpoint_state = self.do_get_pipeline_endpoint(endpoint)
        except PipelineEndpointNotFoundError:
            endpoint_state.status = PipelineEndpointStatus.ABSENT
            endpoint = self._update_pipeline_endpoint(endpoint, endpoint_state)
        except DeployerError as e:
            self._update_pipeline_endpoint(endpoint, endpoint_state)
            raise DeployerError(
                f"Failed to refresh pipeline endpoint {endpoint_name_or_id}: {e}"
            ) from e
        except Exception as e:
            self._update_pipeline_endpoint(endpoint, endpoint_state)
            raise DeployerError(
                f"Unexpected error while refreshing pipeline endpoint for "
                f"{endpoint_name_or_id}: {e}"
            ) from e

        return endpoint

    def deprovision_pipeline_endpoint(
        self,
        endpoint_name_or_id: Union[str, UUID],
        project: Optional[UUID] = None,
        timeout: Optional[int] = None,
    ) -> PipelineEndpointResponse:
        """Deprovision a pipeline endpoint.

        Args:
            endpoint_name_or_id: The name or ID of the pipeline endpoint to
                deprovision.
            project: The project ID of the pipeline endpoint to deprovision.
                Required if a name is provided.
            timeout: The maximum time in seconds to wait for the pipeline
                endpoint to deprovision. If provided, will override the
                deployer's default timeout.

        Returns:
            The pipeline endpoint.

        Raises:
            PipelineEndpointNotFoundError: if the pipeline endpoint is not found
                or is not managed by this deployer.
            DeployerError: if an unexpected error occurs.
        """
        client = Client()
        try:
            endpoint = client.get_pipeline_endpoint(
                endpoint_name_or_id, project=project
            )
        except KeyError:
            raise PipelineEndpointNotFoundError(
                f"Pipeline endpoint with name or ID '{endpoint_name_or_id}' "
                f"not found"
            )

        self._check_pipeline_endpoint_deployer(endpoint)

        if not timeout and endpoint.pipeline_deployment:
            settings = cast(
                BaseDeployerSettings,
                self.get_settings(endpoint.pipeline_deployment),
            )

            timeout = settings.lcm_timeout

        timeout = timeout or DEFAULT_PIPELINE_ENDPOINT_LCM_TIMEOUT

        start_time = time.time()
        endpoint_state = PipelineEndpointOperationalState(
            status=PipelineEndpointStatus.ERROR,
        )
        try:
            deleted_endpoint_state = self.do_deprovision_pipeline_endpoint(
                endpoint, timeout
            )
            if not deleted_endpoint_state:
                # When do_delete_pipeline_endpoint returns a None value, this
                # is to signal that the endpoint is already fully deprovisioned.
                endpoint_state.status = PipelineEndpointStatus.ABSENT
        except PipelineEndpointNotFoundError:
            endpoint_state.status = PipelineEndpointStatus.ABSENT
        except DeployerError as e:
            raise DeployerError(
                f"Failed to delete pipeline endpoint {endpoint_name_or_id}: {e}"
            ) from e
        except Exception as e:
            raise DeployerError(
                f"Unexpected error while deleting pipeline endpoint for "
                f"{endpoint_name_or_id}: {e}"
            ) from e
        finally:
            endpoint = self._update_pipeline_endpoint(endpoint, endpoint_state)

        if endpoint_state.status == PipelineEndpointStatus.ABSENT:
            return endpoint

        # Subtract the time spent deprovisioning the endpoint from the timeout
        timeout = timeout - int(time.time() - start_time)
        endpoint, _ = self._poll_pipeline_endpoint(
            endpoint, PipelineEndpointStatus.ABSENT, timeout
        )

        if endpoint.status != PipelineEndpointStatus.ABSENT:
            raise PipelineEndpointDeprovisionError(
                f"Failed to deprovision pipeline endpoint {endpoint_name_or_id}: "
                f"Operational state: {endpoint.status}"
            )
        return endpoint

    def delete_pipeline_endpoint(
        self,
        endpoint_name_or_id: Union[str, UUID],
        project: Optional[UUID] = None,
        force: bool = False,
        timeout: Optional[int] = None,
    ) -> None:
        """Deprovision and delete a pipeline endpoint.

        Args:
            endpoint_name_or_id: The name or ID of the pipeline endpoint to
                delete.
            project: The project ID of the pipeline endpoint to deprovision.
                Required if a name is provided.
            force: if True, force the pipeline endpoint to delete even if it
                cannot be deprovisioned.
            timeout: The maximum time in seconds to wait for the pipeline
                endpoint to be deprovisioned. If provided, will override the
                deployer's default timeout.

        Raises:
            PipelineEndpointNotFoundError: if the pipeline endpoint is not found
                or is not managed by this deployer.
            DeployerError: if an unexpected error occurs.
        """
        client = Client()
        try:
            endpoint = self.deprovision_pipeline_endpoint(
                endpoint_name_or_id, project, timeout
            )
        except PipelineEndpointNotFoundError:
            # The endpoint was already deleted
            return
        except DeployerError as e:
            if force:
                logger.warning(
                    f"Failed to deprovision pipeline endpoint "
                    f"{endpoint_name_or_id}: {e}. Forcing deletion."
                )
                endpoint = client.get_pipeline_endpoint(
                    endpoint_name_or_id, project=project
                )
                client.zen_store.delete_pipeline_endpoint(
                    endpoint_id=endpoint.id
                )
            else:
                raise
        else:
            client.zen_store.delete_pipeline_endpoint(endpoint_id=endpoint.id)

    def get_pipeline_endpoint_logs(
        self,
        endpoint_name_or_id: Union[str, UUID],
        project: Optional[UUID] = None,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Get the logs of a pipeline endpoint.

        Args:
            endpoint_name_or_id: The name or ID of the pipeline endpoint to get
                the logs of.
            project: The project ID of the pipeline endpoint to get the logs of.
                Required if a name is provided.
            follow: if True, the logs will be streamed as they are written.
            tail: only retrieve the last NUM lines of log output.

        Returns:
            A generator that yields the logs of the pipeline endpoint.

        Raises:
            PipelineEndpointNotFoundError: if the pipeline endpoint is not found.
            DeployerError: if an unexpected error occurs.
        """
        client = Client()
        try:
            endpoint = client.get_pipeline_endpoint(
                endpoint_name_or_id, project=project
            )
        except KeyError:
            raise PipelineEndpointNotFoundError(
                f"Pipeline endpoint with name or ID '{endpoint_name_or_id}' "
                f"not found"
            )

        self._check_pipeline_endpoint_deployer(endpoint)

        try:
            return self.do_get_pipeline_endpoint_logs(endpoint, follow, tail)
        except DeployerError as e:
            raise DeployerError(
                f"Failed to get logs for pipeline endpoint {endpoint_name_or_id}: {e}"
            ) from e
        except Exception as e:
            raise DeployerError(
                f"Unexpected error while getting logs for pipeline endpoint for "
                f"{endpoint_name_or_id}: {e}"
            ) from e

    # ------------------ Abstract Methods ------------------

    @abstractmethod
    def do_provision_pipeline_endpoint(
        self,
        endpoint: PipelineEndpointResponse,
        stack: "Stack",
        environment: Dict[str, str],
        secrets: Dict[str, str],
        timeout: int,
    ) -> PipelineEndpointOperationalState:
        """Abstract method to serve a pipeline as an HTTP endpoint.

        Concrete deployer subclasses must implement the following
        functionality in this method:

        - Create the actual pipeline endpoint infrastructure (e.g.,
        FastAPI server, Kubernetes deployment, cloud function, etc.) based on
        the information in the pipeline endpoint response, particularly the
        pipeline deployment. When determining how to name the external
        resources, do not rely on the endpoint name as being immutable
        or unique.

        - If the pipeline endpoint infrastructure is already deployed, update
        it to match the information in the pipeline endpoint response.

        - Return a PipelineEndpointOperationalState representing the operational
        state of the deployed pipeline endpoint.

        Note that the pipeline endpoint infrastructure is not required to be
        deployed immediately. The deployer can return a
        PipelineEndpointOperationalState with a status of
        PipelineEndpointStatus.PENDING, and the base deployer will poll
        the pipeline endpoint infrastructure by calling the
        `do_get_pipeline_endpoint` method until it is ready or it times out.

        Args:
            endpoint: The pipeline endpoint to serve as an HTTP endpoint.
            stack: The stack the pipeline will be served on.
            environment: A dictionary of environment variables to set on the
                pipeline endpoint.
            secrets: A dictionary of secret environment variables to set
                on the pipeline endpoint. These secret environment variables
                should not be exposed as regular environment variables on the
                deployer.
            timeout: The maximum time in seconds to wait for the pipeline
                endpoint to be deployed.

        Returns:
            The PipelineEndpointOperationalState object representing the
            operational state of the deployed pipeline endpoint.

        Raises:
            PipelineEndpointDeploymentError: if the pipeline endpoint deployment
                fails.
            DeployerError: if an unexpected error occurs.
        """

    @abstractmethod
    def do_get_pipeline_endpoint(
        self,
        endpoint: PipelineEndpointResponse,
    ) -> PipelineEndpointOperationalState:
        """Abstract method to get information about a pipeline endpoint.

        Args:
            endpoint: The pipeline endpoint to get information about.

        Returns:
            The PipelineEndpointOperationalState object representing the
            updated operational state of the pipeline endpoint.

        Raises:
            PipelineEndpointNotFoundError: if no pipeline endpoint is found
                corresponding to the provided PipelineEndpointResponse.
            DeployerError: if the pipeline endpoint information cannot
                be retrieved for any other reason or if an unexpected error
                occurs.
        """

    @abstractmethod
    def do_get_pipeline_endpoint_logs(
        self,
        endpoint: PipelineEndpointResponse,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Abstract method to get the logs of a pipeline endpoint.

        Args:
            endpoint: The pipeline endpoint to get the logs of.
            follow: if True, the logs will be streamed as they are written
            tail: only retrieve the last NUM lines of log output.

        Returns:
            A generator that yields the logs of the pipeline endpoint.

        Raises:
            PipelineEndpointNotFoundError: if no pipeline endpoint is found
                corresponding to the provided PipelineEndpointResponse.
            PipelineLogsNotFoundError: if the pipeline endpoint logs are not
                found.
            DeployerError: if the pipeline endpoint logs cannot
                be retrieved for any other reason or if an unexpected error
                occurs.
        """

    @abstractmethod
    def do_deprovision_pipeline_endpoint(
        self,
        endpoint: PipelineEndpointResponse,
        timeout: int,
    ) -> Optional[PipelineEndpointOperationalState]:
        """Abstract method to deprovision a pipeline endpoint.

        Concrete deployer subclasses must implement the following
        functionality in this method:

        - Deprovision the actual pipeline endpoint infrastructure (e.g.,
        FastAPI server, Kubernetes deployment, cloud function, etc.) based on
        the information in the pipeline endpoint response.

        - Return a PipelineEndpointOperationalState representing the operational
        state of the deleted pipeline endpoint, or None if the deletion is
        completed before the call returns.

        Note that the pipeline endpoint infrastructure is not required to be
        deleted immediately. The deployer can return a
        PipelineEndpointOperationalState with a status of
        PipelineEndpointStatus.PENDING, and the base deployer will poll
        the pipeline endpoint infrastructure by calling the
        `do_get_pipeline_endpoint` method until it is deleted or it times out.

        Args:
            endpoint: The pipeline endpoint to delete.
            timeout: The maximum time in seconds to wait for the pipeline
                endpoint to be deprovisioned.

        Returns:
            The PipelineEndpointOperationalState object representing the
            operational state of the deprovisioned pipeline endpoint, or None
            if the deprovision is completed before the call returns.

        Raises:
            PipelineEndpointNotFoundError: if no pipeline endpoint is found
                corresponding to the provided PipelineEndpointResponse.
            PipelineEndpointDeprovisionError: if the pipeline endpoint
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
