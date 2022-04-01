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

from typing import Any, Dict, Optional, Tuple

from pydantic import Field

from zenml.integrations.seldon.seldon_client import (
    SeldonClient,
    SeldonDeployment,
    SeldonDeploymentNotFoundError,
)
from zenml.logger import get_logger
from zenml.services.service import BaseService, ServiceConfig
from zenml.services.service_status import ServiceState, ServiceStatus
from zenml.services.service_type import ServiceType

logger = get_logger(__name__)


class SeldonDeploymentConfig(ServiceConfig):
    """Seldon Core deployment service configuration.

    Attributes:
        model_uri: URI of the model (or models) to serve
        model_name: the name of the model. Multiple versions of the same model
            should use the same model name
        model_format: the format of the model being served
        protocol: the Seldon Core protocol used to serve the model
        pipeline_name: the name of the pipeline that was used to deploy the
            model
        pipeline_run_id: the ID of the pipeline run that deployed the model
        pipeline_step_name: the name of the pipeline step that deployed the
            model
        replicas: number of replicas to use for the prediction service
        model_metadaa: optional model metadata information (see
            https://docs.seldon.io/projects/seldon-core/en/latest/reference/apis/metadata.html)
        extra_args: additional arguments to pass to the Seldon Core deployment
            resource configuration
    """

    # TODO [HIGH]: determine how to formalize how models are organized into
    #   folders and sub-folders depending on the model type/format and the
    #   Seldon Core protocol used to serve the model.
    model_uri: str
    model_name: str
    # TODO [HIGH]: have an enum of all model formats ?
    model_format: str
    # TODO [HIGH]: have an enum of all supported Seldon Core protocols ?
    protocol: str
    pipeline_name: Optional[str] = None
    pipeline_run_id: Optional[str] = None
    pipeline_step_name: Optional[str] = None
    replicas: int = 1
    model_metadata: Dict[str, Any] = Field(default_factory=dict)
    extra_args: Dict[str, Any] = Field(default_factory=dict)

    # configuration attributes that are not part of the service configuration
    # but are required for the service to function. These must be moved to the
    # stack component, when available
    kubernetes_context: str
    namespace: str
    ingress_hostname: str


class SeldonDeploymentServiceStatus(ServiceStatus):
    """Seldon Core deployment service status.

    Attributes:
        predition_url: the prediction URI exposed by the prediction service
    """

    prediction_url: Optional[str] = None


class SeldonDeploymentService(BaseService):
    """A service that represents a Seldon Core deployment server.


    Attributes:
        config: service configuration
        status: service status
    """

    SERVICE_TYPE = ServiceType(
        name="seldon-deployment",
        type="model-serving",
        flavor="seldon",
        description="Seldon Core prediction service",
    )

    config: SeldonDeploymentConfig = Field(
        default_factory=SeldonDeploymentConfig
    )
    status: SeldonDeploymentServiceStatus = Field(
        default_factory=SeldonDeploymentServiceStatus
    )

    # private attributes

    _client: Optional[SeldonClient] = None

    def _get_client(self) -> SeldonClient:
        """Get the Seldon Core client.

        Returns:
            The Seldon Core client.
        """
        if self._client is None:
            self._client = SeldonClient(
                context=self.config.kubernetes_context,
                namespace=self.config.namespace,
            )

        return self._client

    def check_status(self) -> Tuple[ServiceState, str]:
        """Check the the current operational state of the Seldon Core
        deployment.

        Returns:
            The operational state of the Seldon Core deployment and a message
            providing additional information about that state (e.g. a
            description of the error, if one is encountered).
        """
        client = self._get_client()
        name = self._get_seldon_deployment_name()
        try:
            deployment = client.get_deployment(name=name)
        except SeldonDeploymentNotFoundError:
            if self.admin_state == ServiceState.INACTIVE:
                return (ServiceState.INACTIVE, "")
            return (
                ServiceState.ERROR,
                f"Seldon Core deployment '{name}' not found",
            )

        if self.admin_state == ServiceState.INACTIVE:
            return (ServiceState.PENDING_SHUTDOWN, "")

        if deployment.is_available():
            return (
                ServiceState.ACTIVE,
                f"Seldon Core deployment '{name}' is available",
            )

        if deployment.is_failed():
            return (
                ServiceState.ERROR,
                f"Seldon Core deployment '{name}' failed: "
                f"{deployment.get_error()}",
            )

        pending_message = deployment.get_pending_message() or ""
        return (
            ServiceState.PENDING_STARTUP,
            "Seldon Core deployment is being created: " + pending_message,
        )

    def _get_seldon_deployment_name(self) -> str:
        """Get the name of the Seldon Core deployment that uniquely
        corresponds to this service instance

        Returns:
            The name of the Seldon Core deployment.
        """
        return f"zenml-{str(self.uuid)}"

    def _get_seldon_deployment_labels(self) -> Dict[str, str]:
        """Generate the labels for the Seldon Core deployment from the
        service configuration.

        Returns:
            The labels for the Seldon Core deployment.
        """
        return dict(
            zenml_pipeline_name=self.config.pipeline_name or "",
            zenml_pipeline_run_id=self.config.pipeline_run_id or "",
            zenml_pipeline_step_name=self.config.pipeline_step_name or "",
            zenml_service_uuid=str(self.uuid),
        )

    def provision(self) -> None:
        """Provision or update the remote Seldon Core deployment instance to
        match the current configuration.
        """
        client = self._get_client()
        name = self._get_seldon_deployment_name()
        deployment = SeldonDeployment.build(
            name=name,
            model_uri=self.config.model_uri,
            model_name=self.config.model_name,
            implementation=self.config.protocol,
            labels=self._get_seldon_deployment_labels(),
        )
        deployment.spec.replicas = self.config.replicas
        deployment.spec.predictors[0].replicas = self.config.replicas

        # check if the Seldon deployment already exists
        try:
            client.get_deployment(name=name)
            # update the existing deployment
            client.update_deployment(deployment)
        except SeldonDeploymentNotFoundError:
            # create the deployment
            client.create_deployment(deployment=deployment)

    def deprovision(self, force: bool = False) -> None:
        """Deprovision the remote Seldon Core deployment instance.

        Args:
            force: if True, the remote deployment instance will be
                forcefully deprovisioned.
        """
        client = self._get_client()
        name = self._get_seldon_deployment_name()
        try:
            client.delete_deployment(name=name, force=force)
        except SeldonDeploymentNotFoundError:
            pass

    def update(self, config: SeldonDeploymentConfig) -> None:
        """Update the service configuration.

        Args:
            config: the new service configuration
        """
        self.config = config
        self.provision()
