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
"""Base class for all ZenML pipeline servers."""

import time
from abc import ABC, abstractmethod
from typing import (
    ClassVar,
    Generator,
    Optional,
    Type,
    cast,
)
from uuid import UUID

from zenml.client import Client
from zenml.enums import PipelineEndpointStatus, StackComponentType
from zenml.exceptions import EntityExistsError
from zenml.logger import get_logger
from zenml.models import (
    PipelineDeploymentResponse,
    PipelineEndpointOperationalState,
    PipelineEndpointRequest,
    PipelineEndpointResponse,
    PipelineEndpointUpdate,
)
from zenml.stack import StackComponent
from zenml.stack.flavor import Flavor
from zenml.stack.stack_component import StackComponentConfig

logger = get_logger(__name__)

DEFAULT_PIPELINE_ENDPOINT_LCM_TIMEOUT = 300


class PipelineServerError(Exception):
    """Base class for pipeline server errors."""


class PipelineEndpointAlreadyExistsError(
    EntityExistsError, PipelineServerError
):
    """Error raised when a pipeline endpoint already exists."""


class PipelineEndpointNotFoundError(KeyError, PipelineServerError):
    """Error raised when a pipeline endpoint is not found."""


class PipelineEndpointDeploymentError(PipelineServerError):
    """Error raised when a pipeline endpoint deployment fails."""


class PipelineEndpointDeploymentTimeoutError(PipelineServerError):
    """Error raised when a pipeline endpoint deployment times out."""


class PipelineEndpointDeletionError(PipelineServerError):
    """Error raised when a pipeline endpoint deletion fails."""


class PipelineEndpointDeletionTimeoutError(PipelineServerError):
    """Error raised when a pipeline endpoint deletion times out."""


class PipelineLogsNotFoundError(KeyError, PipelineServerError):
    """Error raised when pipeline logs are not found."""


class BasePipelineServerConfig(StackComponentConfig):
    """Base config for all pipeline servers."""


class BasePipelineServer(StackComponent, ABC):
    """Base class for all ZenML pipeline servers.

    The pipeline server serves three major purposes:

    1. It contains all the stack related configuration attributes required to
    interact with the remote pipeline serving tool, service or platform (e.g.
    hostnames, URLs, references to credentials, other client related
    configuration parameters).

    2. It implements the life-cycle management for pipeline endpoints, including
    discovery, creation, deletion and updating.

    3. It acts as a ZenML pipeline endpoint registry, where every pipeline
    endpoint is stored as a database entity through the ZenML Client. This
    allows the pipeline server to keep track of all externally running pipeline
    endpoints and to manage their lifecycle.
    """

    NAME: ClassVar[str]
    FLAVOR: ClassVar[Type["BasePipelineServerFlavor"]]

    @property
    def config(self) -> BasePipelineServerConfig:
        """Returns the `BasePipelineServerConfig` config.

        Returns:
            The configuration.
        """
        return cast(BasePipelineServerConfig, self._config)

    @classmethod
    def get_active_pipeline_server(cls) -> "BasePipelineServer":
        """Get the pipeline server registered in the active stack.

        Returns:
            The pipeline server registered in the active stack.

        Raises:
            TypeError: if a pipeline server is not part of the
                active stack.
        """
        flavor: BasePipelineServerFlavor = cls.FLAVOR()
        client = Client()
        pipeline_server = client.active_stack.pipeline_server
        if not pipeline_server or not isinstance(pipeline_server, cls):
            raise TypeError(
                f"The active stack needs to have a {cls.NAME} pipeline "
                f"server component registered to be able to deploy pipelines "
                f"with {cls.NAME}. You can create a new stack with "
                f"a {cls.NAME} pipeline server component or update your "
                f"active stack to add this component, e.g.:\n\n"
                f"  `zenml pipeline-server register {flavor.name} "
                f"--flavor={flavor.name} ...`\n"
                f"  `zenml stack register <STACK-NAME> -ps {flavor.name} ...`\n"
                f"  or:\n"
                f"  `zenml stack update -ps {flavor.name}`\n\n"
            )

        return pipeline_server

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
        return client.zen_store.update_pipeline_endpoint(
            endpoint.id,
            PipelineEndpointUpdate.from_operational_state(operational_state),
        )

    def serve_pipeline(
        self,
        deployment: PipelineDeploymentResponse,
        endpoint_name: str,
        replace: bool = True,
        timeout: int = DEFAULT_PIPELINE_ENDPOINT_LCM_TIMEOUT,
    ) -> PipelineEndpointResponse:
        """Serve a pipeline as an HTTP endpoint.

        The serve_pipeline method is the main entry point for serving
        pipelines using the pipeline server. It is used to serve a pipeline
        deployment as an HTTP endpoint, or update an existing pipeline endpoint
        instance with the same name. The method returns a
        PipelineEndpointResponse object that is a representation of the
        external pipeline endpoint instance.

        Args:
            deployment: The pipeline deployment to serve as an HTTP endpoint.
            endpoint_name: Unique name for the pipeline endpoint. This name must
                be unique at the project level.
            replace: If True, it will update in-place any existing pipeline
                endpoint instance with the same name. If False, and the pipeline
                endpoint instance already exists, it will raise a
                PipelineEndpointAlreadyExistsError.
            timeout: The maximum time in seconds to wait for the pipeline
                endpoint to become operational.

        Raises:
            PipelineEndpointAlreadyExistsError: if the pipeline endpoint already
                exists and replace is False.
            PipelineEndpointDeploymentError: if the pipeline deployment fails.
            PipelineEndpointDeploymentTimeoutError: if the pipeline endpoint
                deployment times out while waiting to become operational.
            PipelineServerError: if an unexpected error occurs.

        Returns:
            The PipelineEndpointResponse object representing the deployed
            pipeline endpoint.
        """
        client = Client()

        logger.debug(
            f"Deploying pipeline endpoint for {endpoint_name} with "
            f"deployment ID: {deployment.id}"
        )

        # Create the pipeline endpoint request
        endpoint_request = PipelineEndpointRequest(
            name=endpoint_name,
            project=deployment.project_id,
            pipeline_deployment_id=deployment.id,
            pipeline_server_id=self.id,  # This pipeline server's ID
        )

        try:
            endpoint = client.zen_store.create_pipeline_endpoint(
                endpoint_request
            )
            logger.debug(
                f"Created new pipeline endpoint with name '{endpoint_name}'"
            )
        except EntityExistsError:
            if not replace:
                raise PipelineEndpointAlreadyExistsError(
                    f"A pipeline endpoint with name '{endpoint_name}' already "
                    "exists"
                )
            try:
                # Get the existing pipeline endpoint
                endpoint = client.get_pipeline_endpoint(
                    endpoint_name, project=deployment.project_id
                )
            except KeyError:
                # Not supposed to happen, but just in case
                raise PipelineServerError(
                    f"A pipeline endpoint with name '{endpoint_name}' already "
                    "exists, but it cannot be found"
                )

            logger.debug(
                f"Existing pipeline endpoint found with name '{endpoint_name}'"
            )

        logger.debug(
            f"Deploying pipeline endpoint {endpoint_name} with "
            f"deployment ID: {deployment.id}"
        )

        endpoint_state = PipelineEndpointOperationalState(
            status=PipelineEndpointStatus.ERROR,
        )
        try:
            endpoint_state = self.do_serve_pipeline(endpoint)
        except PipelineEndpointDeploymentError as e:
            self._update_pipeline_endpoint(endpoint, endpoint_state)
            raise PipelineEndpointDeploymentError(
                f"Failed to deploy pipeline endpoint for {endpoint_name}: {e}"
            ) from e
        except PipelineServerError as e:
            self._update_pipeline_endpoint(endpoint, endpoint_state)
            raise PipelineServerError(
                f"Failed to deploy pipeline endpoint for {endpoint_name}: {e}"
            ) from e
        except Exception as e:
            self._update_pipeline_endpoint(endpoint, endpoint_state)
            raise PipelineServerError(
                f"Unexpected error while deploying pipeline endpoint for "
                f"{endpoint_name}: {e}"
            ) from e

        logger.debug(
            f"Deployed pipeline endpoint for {endpoint_name} with "
            f"deployment ID: {deployment.id}. Operational state: "
            f"{endpoint_state.status}"
        )

        start_time = time.time()
        sleep_time = 5
        while endpoint_state.status == PipelineEndpointStatus.DEPLOYING:
            if time.time() - start_time > timeout:
                raise PipelineEndpointDeploymentTimeoutError(
                    f"Deployment of pipeline endpoint for {endpoint_name} "
                    f"timed out after {timeout} seconds"
                )
            logger.debug(
                f"Pipeline endpoint for {endpoint_name} is not yet running. "
                f"Waiting for {sleep_time} seconds..."
            )
            time.sleep(sleep_time)
            endpoint_state = self.do_get_pipeline_endpoint(endpoint)
            endpoint = self._update_pipeline_endpoint(endpoint, endpoint_state)

        if endpoint_state.status != PipelineEndpointStatus.RUNNING:
            raise PipelineEndpointDeploymentError(
                f"Failed to deploy pipeline endpoint for {endpoint_name}: "
                f"Operational state: {endpoint_state.status}"
            )

        return endpoint

    def refresh_pipeline_endpoint(
        self,
        endpoint_name_or_id: str,
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
            PipelineServerError: if an unexpected error occurs.
        """
        client = Client()
        try:
            endpoint = client.get_pipeline_endpoint(
                endpoint_name_or_id, project=project
            )
        except KeyError:
            raise PipelineEndpointNotFoundError(
                f"Pipeline endpoint with name or ID '{endpoint_name_or_id}' "
                f"not found in project {project}"
            )

        endpoint_state = PipelineEndpointOperationalState(
            status=PipelineEndpointStatus.ERROR,
        )
        try:
            endpoint_state = self.do_get_pipeline_endpoint(endpoint)
        except PipelineEndpointNotFoundError:
            endpoint_state.status = PipelineEndpointStatus.DELETED
            self._update_pipeline_endpoint(endpoint, endpoint_state)
            raise PipelineEndpointNotFoundError(
                f"Pipeline endpoint with name or ID '{endpoint_name_or_id}' "
                f"not found in project {project}"
            )
        except PipelineServerError as e:
            self._update_pipeline_endpoint(endpoint, endpoint_state)
            raise PipelineServerError(
                f"Failed to refresh pipeline endpoint for {endpoint_name_or_id}: {e}"
            ) from e
        except Exception as e:
            self._update_pipeline_endpoint(endpoint, endpoint_state)
            raise PipelineServerError(
                f"Unexpected error while refreshing pipeline endpoint for "
                f"{endpoint_name_or_id}: {e}"
            ) from e

        return self._update_pipeline_endpoint(endpoint, endpoint_state)

    def delete_pipeline_endpoint(
        self,
        endpoint_name_or_id: str,
        project: Optional[UUID] = None,
        timeout: int = DEFAULT_PIPELINE_ENDPOINT_LCM_TIMEOUT,
    ) -> None:
        """Delete a pipeline endpoint.

        Args:
            endpoint_name_or_id: The name or ID of the pipeline endpoint to delete.
            project: The project ID of the pipeline endpoint to delete. Required
                if a name is provided.
            timeout: The maximum time in seconds to wait for the pipeline
                endpoint to stop.

        Raises:
            PipelineEndpointNotFoundError: if the pipeline endpoint is not found.
            PipelineServerError: if an unexpected error occurs.
        """
        client = Client()
        try:
            endpoint = client.get_pipeline_endpoint(
                endpoint_name_or_id, project=project
            )
        except KeyError:
            raise PipelineEndpointNotFoundError(
                f"Pipeline endpoint with name or ID '{endpoint_name_or_id}' "
                f"not found in project {project}"
            )

        endpoint_state = (
            PipelineEndpointOperationalState(
                status=PipelineEndpointStatus.ERROR,
            )
        )
        try:
            deleted_endpoint_state = self.do_delete_pipeline_endpoint(endpoint)
        except PipelineEndpointNotFoundError:
            client.delete_pipeline_endpoint(endpoint.id)
            raise PipelineEndpointNotFoundError(
                f"Pipeline endpoint with name or ID '{endpoint_name_or_id}' "
                f"not found in project {project}"
            )
        except PipelineServerError as e:
            self._update_pipeline_endpoint(endpoint, endpoint_state)
            raise PipelineServerError(
                f"Failed to delete pipeline endpoint for {endpoint_name_or_id}: {e}"
            ) from e
        except Exception as e:
            self._update_pipeline_endpoint(endpoint, endpoint_state)
            raise PipelineServerError(
                f"Unexpected error while deleting pipeline endpoint for "
                f"{endpoint_name_or_id}: {e}"
            ) from e

        if not deleted_endpoint_state:
            # The endpoint was already fully deleted by the time the call to
            # do_delete_pipeline_endpoint returned.
            client.delete_pipeline_endpoint(endpoint.id)
            return

        endpoint_state = deleted_endpoint_state

        start_time = time.time()
        sleep_time = 5
        while endpoint_state.status == PipelineEndpointStatus.DELETING:
            if time.time() - start_time > timeout:
                raise PipelineEndpointDeletionTimeoutError(
                    f"Deletion of pipeline endpoint for {endpoint_name_or_id} "
                    f"timed out after {timeout} seconds"
                )
            logger.debug(
                f"Pipeline endpoint for {endpoint_name_or_id} is not yet deleted. "
                f"Waiting for {sleep_time} seconds..."
            )
            time.sleep(sleep_time)
            endpoint_state = self.do_get_pipeline_endpoint(endpoint)
            endpoint = self._update_pipeline_endpoint(endpoint, endpoint_state)

        if endpoint_state.status != PipelineEndpointStatus.DELETED:
            raise PipelineEndpointDeletionError(
                f"Failed to delete pipeline endpoint for {endpoint_name_or_id}: "
                f"Operational state: {endpoint_state.status}"
            )

        client.delete_pipeline_endpoint(endpoint.id)

    def get_pipeline_endpoint_logs(
        self,
        endpoint_name_or_id: str,
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
            PipelineServerError: if an unexpected error occurs.
        """
        client = Client()
        try:
            endpoint = client.get_pipeline_endpoint(
                endpoint_name_or_id, project=project
            )
        except KeyError:
            raise PipelineEndpointNotFoundError(
                f"Pipeline endpoint with name or ID '{endpoint_name_or_id}' "
                f"not found in project {project}"
            )

        try:
            return self.do_get_pipeline_endpoint_logs(endpoint, follow, tail)
        except PipelineServerError as e:
            raise PipelineServerError(
                f"Failed to get logs for pipeline endpoint for {endpoint_name_or_id}: {e}"
            ) from e
        except Exception as e:
            raise PipelineServerError(
                f"Unexpected error while getting logs for pipeline endpoint for "
                f"{endpoint_name_or_id}: {e}"
            ) from e

    # ------------------ Abstract Methods ------------------

    @abstractmethod
    def do_serve_pipeline(
        self,
        endpoint: PipelineEndpointResponse,
    ) -> PipelineEndpointOperationalState:
        """Abstract method to serve a pipeline as an HTTP endpoint.

        Concrete pipeline server subclasses must implement the following
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
        deployed immediately. The pipeline server can return a
        PipelineEndpointOperationalState with a status of
        PipelineEndpointStatus.DEPLOYING, and the base pipeline server will poll
        the pipeline endpoint infrastructure by calling the
        `do_get_pipeline_endpoint` method until it is ready or it times out.

        Args:
            endpoint: The pipeline endpoint to serve as an HTTP endpoint.

        Returns:
            The PipelineEndpointOperationalState object representing the
            operational state of the deployed pipeline endpoint.

        Raises:
            PipelineEndpointDeploymentError: if the pipeline endpoint deployment
                fails.
            PipelineServerError: if an unexpected error occurs.
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
            PipelineServerError: if the pipeline endpoint information cannot
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
            PipelineServerError: if the pipeline endpoint logs cannot
                be retrieved for any other reason or if an unexpected error
                occurs.
        """

    @abstractmethod
    def do_delete_pipeline_endpoint(
        self,
        endpoint: PipelineEndpointResponse,
    ) -> Optional[PipelineEndpointOperationalState]:
        """Abstract method to delete a pipeline endpoint.

        Concrete pipeline server subclasses must implement the following
        functionality in this method:

        - Delete the actual pipeline endpoint infrastructure (e.g.,
        FastAPI server, Kubernetes deployment, cloud function, etc.) based on
        the information in the pipeline endpoint response.

        - Return a PipelineEndpointOperationalState representing the operational
        state of the deleted pipeline endpoint, or None if the deletion is
        completed before the call returns.

        Note that the pipeline endpoint infrastructure is not required to be
        deleted immediately. The pipeline server can return a
        PipelineEndpointOperationalState with a status of
        PipelineEndpointStatus.DELETING, and the base pipeline server will poll
        the pipeline endpoint infrastructure by calling the
        `do_get_pipeline_endpoint` method until it is deleted or it times out.

        Args:
            endpoint: The pipeline endpoint to delete.

        Returns:
            The PipelineEndpointOperationalState object representing the
            operational state of the deleted pipeline endpoint, or None if the
            deletion is completed before the call returns.

        Raises:
            PipelineEndpointNotFoundError: if no pipeline endpoint is found
                corresponding to the provided PipelineEndpointResponse.
            PipelineEndpointDeletionError: if the pipeline endpoint deletion
                fails.
            PipelineServerError: if an unexpected error occurs.
        """


class BasePipelineServerFlavor(Flavor):
    """Base class for pipeline server flavors."""

    @property
    def type(self) -> StackComponentType:
        """Returns the flavor type.

        Returns:
            The flavor type.
        """
        return StackComponentType.PIPELINE_SERVER

    @property
    def config_class(self) -> Type[BasePipelineServerConfig]:
        """Returns `BasePipelineServerConfig` config class.

        Returns:
                The config class.
        """
        return BasePipelineServerConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type[BasePipelineServer]:
        """The class that implements the pipeline server."""
