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
"""Implementation for the Seldon V2 services."""

import json
import os
from typing import Any, Dict, Generator, List, Optional, Tuple, cast
from uuid import UUID

import requests
from pydantic import Field, ValidationError

from zenml import __version__
from zenml.integrations.seldon_v2.seldon_v2_client import (
    SeldonV2Client,
    SeldonV2Model,
    SeldonV2ModelNotFoundError,
    SeldonV2ModelParameter,
)
from zenml.logger import get_logger
from zenml.services.service import BaseDeploymentService, ServiceConfig
from zenml.services.service_status import ServiceState, ServiceStatus
from zenml.services.service_type import ServiceType

logger = get_logger(__name__)


class SeldonV2ModelConfig(ServiceConfig):
    """Seldon Core V2 Model service configuration.

    Attributes:
        model_uri: URI of the model (or models) to serve.
        name: the name of the model. Multiple versions of the same model
            should use the same model name.
        requirements: list which provides tags that need to be matched by the Server that can run this artifact type.
        replicas: number of replicas to use for the prediction service.
        secret_name: the name of a Kubernetes secret containing additional
            configuration parameters for the Seldon Core model (e.g.
            credentials to access the Artifact Store).
        model_metadata: optional model metadata information (see
            https://docs.seldon.io/projects/seldon-core/en/latest/reference/apis/metadata.html).
        replicas: number of replicas to use for the prediction service.
        memory: memory limit for the prediction service.
        parameters: list of parameters to pass to the model.
    """

    model_uri: str
    name: str
    requirements: List[str] = []
    parameters: Optional[List[SeldonV2ModelParameter]]
    secret_name: Optional[str]
    model_metadata: Dict[str, Any] = Field(default_factory=dict)
    memory: Optional[str]
    replicas: Optional[int]

    def get_seldon_model_labels(self) -> Dict[str, str]:
        """Generate labels for the Seldon Core V2 model from the service configuration.

        These labels are attached to the Seldon Core V2 model resource
        and may be used as label selectors in lookup operations.

        Returns:
            The labels for the Seldon Core V2 model.
        """
        labels = {}
        if self.pipeline_name:
            labels["zenml.pipeline_name"] = self.pipeline_name
        if self.run_name:
            labels["zenml.run_name"] = self.run_name
        if self.pipeline_step_name:
            labels["zenml.pipeline_step_name"] = self.pipeline_step_name
        if self.name:
            labels["zenml.name"] = self.name
        if self.model_uri:
            labels["zenml.model_uri"] = self.model_uri
        if self.requirements:
            labels["zenml.requirements"] = ", ".join(self.requirements)
        SeldonV2Client.sanitize_labels(labels)
        return labels

    def get_seldon_model_annotations(self) -> Dict[str, str]:
        """Generate annotations for the Seldon Core V2 model from the service configuration.

        The annotations are used to store additional information about the
        Seldon Core service that is associated with the model that is
        not available in the labels. One annotation particularly important
        is the serialized Service configuration itself, which is used to
        recreate the service configuration from a remote Seldon model.

        Returns:
            The annotations for the Seldon Core model.
        """
        annotations = {
            "zenml.service_config": self.json(),
            "zenml.version": __version__,
        }
        return annotations

    @classmethod
    def create_from_model(cls, model: SeldonV2Model) -> "SeldonV2ModelConfig":
        """Recreate the configuration of a Seldon Core Service from a deployed instance.

        Args:
            model: the Seldon Core V2 Model resource.

        Returns:
            The Seldon Core V2 service configuration corresponding to the given
            Seldon Core V2 Model resource.

        Raises:
            ValueError: if the given model resource does not contain
                the expected annotations or it contains an invalid or
                incompatible Seldon Core V2 service configuration.
        """
        config_data = model.metadata.annotations.get("zenml.service_config")
        if not config_data:
            raise ValueError(
                f"The given model resource does not contain a "
                f"'zenml.service_config' annotation: {model}"
            )
        try:
            service_config = cls.parse_raw(config_data)
        except ValidationError as e:
            raise ValueError(
                f"The loaded Seldon Core V2 model resource contains an "
                f"invalid or incompatible Seldon Core V2 service configuration: "
                f"{config_data}"
            ) from e
        return service_config


class SeldonV2ModelServiceStatus(ServiceStatus):
    """Seldon Core V2 model service status."""


class SeldonV2ModelService(BaseDeploymentService):
    """A service that represents a Seldon Core V2 model server.

    Attributes:
        config: service configuration.
        status: service status.
    """

    SERVICE_TYPE = ServiceType(
        name="seldon-v2-model",
        type="model-serving",
        flavor="seldon_v2",
        description="Seldon Core V2 prediction service",
    )

    config: SeldonV2ModelConfig
    status: SeldonV2ModelServiceStatus = Field(
        default_factory=lambda: SeldonV2ModelServiceStatus()
    )

    def _get_client(self) -> SeldonV2Client:
        """Get the Seldon Core V2 client from the active Seldon Core V2 model deployer.

        Returns:
            The Seldon Core V2 client.
        """
        from zenml.integrations.seldon_v2.model_deployers.seldon_v2_model_deployer import (
            SeldonV2ModelDeployer,
        )

        model_deployer = cast(
            SeldonV2ModelDeployer,
            SeldonV2ModelDeployer.get_active_model_deployer(),
        )
        return model_deployer.seldon_v2_client

    def check_status(self) -> Tuple[ServiceState, str]:
        """Check the the current operational state of the Seldon Core V2.

        Returns:
            The operational state of the Seldon Core V2 model and a message
            providing additional information about that state (e.g. a
            description of the error, if one is encountered).
        """
        client = self._get_client()
        name = self.seldon_name
        try:
            model = client.get_model(name=name)
        except SeldonV2ModelNotFoundError:
            return (ServiceState.INACTIVE, "")

        if model.is_available():
            return (
                ServiceState.ACTIVE,
                f"Seldon Core V2 model '{name}' is available",
            )

        if model.is_failed():
            return (
                ServiceState.ERROR,
                f"Seldon Core V2 model '{name}' failed: "
                f"{model.get_error()}",
            )

        pending_message = model.get_pending_message() or ""
        return (
            ServiceState.PENDING_STARTUP,
            "Seldon Core V2 model is being created: " + pending_message,
        )

    @property
    def seldon_name(self) -> str:
        """Get the name of the Seldon Core V2 Model.

        It should return the one that uniquely corresponds to this service instance.

        Returns:
            The name of the Seldon Core v2 model.
        """
        return f"zenml-{str(self.uuid)}"

    def _get_seldon_model_labels(self) -> Dict[str, str]:
        """Generate the labels for the Seldon Core v2 model from the service configuration.

        Returns:
            The labels for the Seldon Core V2 model.
        """
        labels = self.config.get_seldon_model_labels()
        labels["zenml.service_uuid"] = str(self.uuid)
        SeldonV2Client.sanitize_labels(labels)
        return labels

    @classmethod
    def create_from_model(cls, model: SeldonV2Model) -> "SeldonV2ModelService":
        """Recreate a Seldon Core service from a Seldon Core V2 model resource.

        It should then update their operational status.

        Args:
            model: the Seldon Core V2 model resource.

        Returns:
            The Seldon Core service corresponding to the given
            Seldon Core V2 model resource.

        Raises:
            ValueError: if the given model resource does not contain
                the expected service_uuid label.
        """
        config = SeldonV2ModelConfig.create_from_model(model)
        uuid = model.metadata.labels.get("zenml.service_uuid")
        if not uuid:
            raise ValueError(
                f"The given model resource does not contain a valid "
                f"'zenml.service_uuid' label: {model}"
            )
        service = cls(uuid=UUID(uuid), config=config)
        service.update_status()
        return service

    def provision(self) -> None:
        """Provision or update remote Seldon Core V2 model instance.

        This should then match the current configuration.
        """
        client = self._get_client()

        name = self.seldon_name

        model = SeldonV2Model.build(
            name=name,
            model_uri=self.config.model_uri,
            requirements=self.config.requirements,
            parameters=self.config.parameters,
            secret_name=self.config.secret_name,
            labels=self._get_seldon_model_labels(),
            annotations=self.config.get_seldon_model_annotations(),
            replicas=self.config.replicas,
            memory=self.config.memory,
        )

        # check if the Seldon V2 model already exists
        try:
            client.get_model(name=name)
            # update the existing model
            client.update_model(model)
        except SeldonV2ModelNotFoundError:
            # create the model
            client.create_model(model=model)

    def deprovision(self, force: bool = False) -> None:
        """Deprovision the remote Seldon Core model instance.

        Args:
            force: if True, the remote model instance will be
                forcefully deprovisioned.
        """
        client = self._get_client()
        name = self.seldon_name
        try:
            client.delete_model(name=name, force=force)
        except SeldonV2ModelNotFoundError:
            pass

    def get_logs(
        self,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Get the logs of a Seldon Core model model.

        Args:
            follow: if True, the logs will be streamed as they are written
            tail: only retrieve the last NUM lines of log output.

        Returns:
            A generator that can be accessed to get the service logs.
        """
        return self._get_client().get_model_logs(
            self.seldon_name,
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
        from zenml.integrations.seldon_v2.model_deployers.seldon_v2_model_deployer import (
            SeldonV2ModelDeployer,
        )

        if not self.is_running:
            return None
        namespace = self._get_client().namespace
        model_deployer = cast(
            SeldonV2ModelDeployer,
            SeldonV2ModelDeployer.get_active_model_deployer(),
        )
        return os.path.join(
            model_deployer.config.base_url,
            "seldon",
            namespace,
            self.seldon_name,
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
        response = requests.post(
            self.prediction_url,
            json={"data": {"ndarray": request}},
        )
        response.raise_for_status()
        return response.json()
