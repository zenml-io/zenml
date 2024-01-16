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
"""Implementation for the Seldon Deployment step."""

import json
import os
from typing import Any, Dict, Generator, List, Optional, Tuple, cast
from uuid import UUID

import requests
from pydantic import Field, ValidationError

from zenml import __version__
from zenml.integrations.seldon.seldon_client import (
    SeldonClient,
    SeldonDeployment,
    SeldonDeploymentNotFoundError,
    SeldonDeploymentPredictorParameter,
    SeldonResourceRequirements,
)
from zenml.logger import get_logger
from zenml.services.service import BaseDeploymentService, ServiceConfig
from zenml.services.service_status import ServiceState, ServiceStatus
from zenml.services.service_type import ServiceType

logger = get_logger(__name__)


class SeldonDeploymentConfig(ServiceConfig):
    """Seldon Core deployment service configuration.

    Attributes:
        model_uri: URI of the model (or models) to serve.
        model_name: the name of the model. Multiple versions of the same model
            should use the same model name.
        implementation: the Seldon Core implementation used to serve the model.
            The implementation type can be one of the following: `TENSORFLOW_SERVER`,
            `SKLEARN_SERVER`, `XGBOOST_SERVER`, `custom`.
        replicas: number of replicas to use for the prediction service.
        secret_name: the name of a Kubernetes secret containing additional
            configuration parameters for the Seldon Core deployment (e.g.
            credentials to access the Artifact Store).
        model_metadata: optional model metadata information (see
            https://docs.seldon.io/projects/seldon-core/en/latest/reference/apis/metadata.html).
        extra_args: additional arguments to pass to the Seldon Core deployment
            resource configuration.
        is_custom_deployment: whether the deployment is a custom deployment
        spec: custom Kubernetes resource specification for the Seldon Core
        serviceAccountName: The name of the Service Account applied to the deployment.
    """

    model_uri: str = ""
    model_name: str = "default"
    # TODO [ENG-775]: have an enum of all supported Seldon Core implementations
    implementation: str
    parameters: Optional[List[SeldonDeploymentPredictorParameter]]
    resources: Optional[SeldonResourceRequirements]
    replicas: int = 1
    secret_name: Optional[str]
    model_metadata: Dict[str, Any] = Field(default_factory=dict)
    extra_args: Dict[str, Any] = Field(default_factory=dict)
    is_custom_deployment: Optional[bool] = False
    spec: Optional[Dict[Any, Any]] = Field(default_factory=dict)
    serviceAccountName: Optional[str] = None

    def get_seldon_deployment_labels(self) -> Dict[str, str]:
        """Generate labels for the Seldon Core deployment from the service configuration.

        These labels are attached to the Seldon Core deployment resource
        and may be used as label selectors in lookup operations.

        Returns:
            The labels for the Seldon Core deployment.
        """
        labels = {}
        if self.pipeline_name:
            labels["zenml.pipeline_name"] = self.pipeline_name
        if self.run_name:
            labels["zenml.run_name"] = self.run_name
        if self.pipeline_step_name:
            labels["zenml.pipeline_step_name"] = self.pipeline_step_name
        if self.model_name:
            labels["zenml.model_name"] = self.model_name
        if self.model_uri:
            labels["zenml.model_uri"] = self.model_uri
        if self.implementation:
            labels["zenml.model_type"] = self.implementation
        if self.extra_args:
            for key, value in self.extra_args.items():
                labels[f"zenml.{key}"] = value
        SeldonClient.sanitize_labels(labels)
        return labels

    def get_seldon_deployment_annotations(self) -> Dict[str, str]:
        """Generate annotations for the Seldon Core deployment from the service configuration.

        The annotations are used to store additional information about the
        Seldon Core service that is associated with the deployment that is
        not available in the labels. One annotation particularly important
        is the serialized Service configuration itself, which is used to
        recreate the service configuration from a remote Seldon deployment.

        Returns:
            The annotations for the Seldon Core deployment.
        """
        annotations = {
            "zenml.service_config": self.json(),
            "zenml.version": __version__,
        }
        return annotations

    @classmethod
    def create_from_deployment(
        cls, deployment: SeldonDeployment
    ) -> "SeldonDeploymentConfig":
        """Recreate the configuration of a Seldon Core Service from a deployed instance.

        Args:
            deployment: the Seldon Core deployment resource.

        Returns:
            The Seldon Core service configuration corresponding to the given
            Seldon Core deployment resource.

        Raises:
            ValueError: if the given deployment resource does not contain
                the expected annotations or it contains an invalid or
                incompatible Seldon Core service configuration.
        """
        config_data = deployment.metadata.annotations.get(
            "zenml.service_config"
        )
        if not config_data:
            raise ValueError(
                f"The given deployment resource does not contain a "
                f"'zenml.service_config' annotation: {deployment}"
            )
        try:
            service_config = cls.parse_raw(config_data)
        except ValidationError as e:
            raise ValueError(
                f"The loaded Seldon Core deployment resource contains an "
                f"invalid or incompatible Seldon Core service configuration: "
                f"{config_data}"
            ) from e
        return service_config


class SeldonDeploymentServiceStatus(ServiceStatus):
    """Seldon Core deployment service status."""


class SeldonDeploymentService(BaseDeploymentService):
    """A service that represents a Seldon Core deployment server.

    Attributes:
        config: service configuration.
        status: service status.
    """

    SERVICE_TYPE = ServiceType(
        name="seldon-deployment",
        type="model-serving",
        flavor="seldon",
        description="Seldon Core prediction service",
    )

    config: SeldonDeploymentConfig
    status: SeldonDeploymentServiceStatus = Field(
        default_factory=lambda: SeldonDeploymentServiceStatus()
    )

    def _get_client(self) -> SeldonClient:
        """Get the Seldon Core client from the active Seldon Core model deployer.

        Returns:
            The Seldon Core client.
        """
        from zenml.integrations.seldon.model_deployers.seldon_model_deployer import (
            SeldonModelDeployer,
        )

        model_deployer = cast(
            SeldonModelDeployer,
            SeldonModelDeployer.get_active_model_deployer(),
        )
        return model_deployer.seldon_client

    def check_status(self) -> Tuple[ServiceState, str]:
        """Check the the current operational state of the Seldon Core deployment.

        Returns:
            The operational state of the Seldon Core deployment and a message
            providing additional information about that state (e.g. a
            description of the error, if one is encountered).
        """
        client = self._get_client()
        name = self.seldon_deployment_name
        try:
            deployment = client.get_deployment(name=name)
        except SeldonDeploymentNotFoundError:
            return (ServiceState.INACTIVE, "")

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

    @property
    def seldon_deployment_name(self) -> str:
        """Get the name of the Seldon Core deployment.

        It should return the one that uniquely corresponds to this service instance.

        Returns:
            The name of the Seldon Core deployment.
        """
        return f"zenml-{str(self.uuid)}"

    def _get_seldon_deployment_labels(self) -> Dict[str, str]:
        """Generate the labels for the Seldon Core deployment from the service configuration.

        Returns:
            The labels for the Seldon Core deployment.
        """
        labels = self.config.get_seldon_deployment_labels()
        labels["zenml.service_uuid"] = str(self.uuid)
        SeldonClient.sanitize_labels(labels)
        return labels

    @classmethod
    def create_from_deployment(
        cls, deployment: SeldonDeployment
    ) -> "SeldonDeploymentService":
        """Recreate a Seldon Core service from a Seldon Core deployment resource.

        It should then update their operational status.

        Args:
            deployment: the Seldon Core deployment resource.

        Returns:
            The Seldon Core service corresponding to the given
            Seldon Core deployment resource.

        Raises:
            ValueError: if the given deployment resource does not contain
                the expected service_uuid label.
        """
        config = SeldonDeploymentConfig.create_from_deployment(deployment)
        uuid = deployment.metadata.labels.get("zenml.service_uuid")
        if not uuid:
            raise ValueError(
                f"The given deployment resource does not contain a valid "
                f"'zenml.service_uuid' label: {deployment}"
            )
        service = cls(uuid=UUID(uuid), config=config)
        service.update_status()
        return service

    def provision(self) -> None:
        """Provision or update remote Seldon Core deployment instance.

        This should then match the current configuration.
        """
        client = self._get_client()

        name = self.seldon_deployment_name

        deployment = SeldonDeployment.build(
            name=name,
            model_uri=self.config.model_uri,
            model_name=self.config.model_name,
            implementation=self.config.implementation,
            parameters=self.config.parameters,
            engineResources=self.config.resources,
            secret_name=self.config.secret_name,
            labels=self._get_seldon_deployment_labels(),
            annotations=self.config.get_seldon_deployment_annotations(),
            is_custom_deployment=self.config.is_custom_deployment,
            spec=self.config.spec,
            serviceAccountName=self.config.serviceAccountName,
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
        name = self.seldon_deployment_name
        try:
            client.delete_deployment(name=name, force=force)
        except SeldonDeploymentNotFoundError:
            pass

    def get_logs(
        self,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Get the logs of a Seldon Core model deployment.

        Args:
            follow: if True, the logs will be streamed as they are written
            tail: only retrieve the last NUM lines of log output.

        Returns:
            A generator that can be accessed to get the service logs.
        """
        return self._get_client().get_deployment_logs(
            self.seldon_deployment_name,
            follow=follow,
            tail=tail,
        )

    @property
    def prediction_url(self) -> Optional[str]:
        """The prediction URI exposed by the prediction service.

        Returns:
            The prediction URI exposed by the prediction service, or None if
            the service is not yet ready.
        """
        from zenml.integrations.seldon.model_deployers.seldon_model_deployer import (
            SeldonModelDeployer,
        )

        if not self.is_running:
            return None
        namespace = self._get_client().namespace
        model_deployer = cast(
            SeldonModelDeployer,
            SeldonModelDeployer.get_active_model_deployer(),
        )
        return os.path.join(
            model_deployer.config.base_url,
            "seldon",
            namespace,
            self.seldon_deployment_name,
            "api/v0.1/predictions",
        )

    def predict(self, request: str) -> Any:
        """Make a prediction using the service.

        Args:
            request: a numpy array representing the request

        Returns:
            A numpy array representing the prediction returned by the service.

        Raises:
            Exception: if the service is not yet ready.
            ValueError: if the prediction_url is not set.
        """
        if not self.is_running:
            raise Exception(
                "Seldon prediction service is not running. "
                "Please start the service before making predictions."
            )

        if self.prediction_url is None:
            raise ValueError("`self.prediction_url` is not set, cannot post.")

        if isinstance(request, str):
            request = json.loads(request)
        else:
            raise ValueError("Request must be a json string.")
        response = requests.post(  # nosec
            self.prediction_url,
            json={"data": {"ndarray": request}},
        )
        response.raise_for_status()
        return response.json()
