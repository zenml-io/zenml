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
"""Implementation of the Seldon V2 client for ZenML."""

import base64
import json
import re
import time
from typing import Any, Dict, Generator, List, Optional

from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from pydantic import BaseModel, Field, ValidationError

from zenml.logger import get_logger
from zenml.utils.enum_utils import StrEnum

logger = get_logger(__name__)

api = k8s_client.ApiClient()

SELDON_V2_MODEL_KIND = "Model"
SELDON_V2_EXPERIMENT_KIND = "Experiment"
SELDON_V2_PIPELINE_KIND = "Pipeline"
SELDON_V2_API_VERSION = "mlops.seldon.io/v1alpha1"


class SeldonV2ModelParameter(BaseModel):
    """Parameter for Seldon V2 Model parameter.

    Attributes:
        name: parameter name
        type: parameter, can be INT, FLOAT, DOUBLE, STRING, BOOL
        value: parameter value
    """

    name: str = ""
    type: str = ""
    value: str = ""

    class Config:
        """Pydantic configuration class."""

        # validate attribute assignments
        validate_assignment = True
        # Ignore extra attributes from the CRD that are not reflected here
        extra = "ignore"


class SeldonV2ModelMetadata(BaseModel):
    """Metadata for a Seldon V2 Model.

    Attributes:
        name: the name of the Seldon V2 Model.
        labels: Kubernetes labels for the Seldon V2 Model.
        annotations: Kubernetes annotations for the Seldon V2 Model.
        creationTimestamp: the creation timestamp of the Seldon V2 Model.
    """

    name: str
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)
    creationTimestamp: Optional[str] = None

    class Config:
        """Pydantic configuration class."""

        # validate attribute assignments
        validate_assignment = True
        # Ignore extra attributes from the CRD that are not reflected here
        extra = "ignore"


class SeldonV2ModelSpec(BaseModel):
    """Spec for a Seldon V2 Model.

    Attributes:
        model_uri: the storage URI for the Seldon V2 Model.
        requirements: the requirements for the Seldon V2 Model.
        memory: the memory for the Seldon V2 Model.
        replicas: the number of replicas for the Seldon V2 Model.
        server: the server for the Seldon V2 Model.
    """

    storage_uri: str
    requirements: List[str]
    memory: Optional[str]
    replicas: Optional[int] = 1
    server: Optional[str]
    parameters: Optional[List[SeldonV2ModelParameter]] = None

    class Config:
        """Pydantic configuration class."""

        # validate attribute assignments
        validate_assignment = True
        # Ignore extra attributes from the CRD that are not reflected here
        extra = "ignore"


class SeldonV2ModelStatusState(StrEnum):
    """Possible state values for a Seldon V2 Model."""

    UNKNOWN = "Unknown"
    AVAILABLE = "Available"
    CREATING = "Creating"
    FAILED = "Failed"


class SeldonV2ModelStatusAddress(BaseModel):
    """The status address for a Seldon V2 Model.

    Attributes:
        url: the URL where the Seldon V2 Model API can be accessed internally.
    """

    url: str


class SeldonV2ModelStatusCondition(BaseModel):
    """The Kubernetes status condition entry for a Seldon V2 Model.

    Attributes:
        type: Type of runtime condition.
        status: Status of the condition.
        reason: Brief CamelCase string containing reason for the condition's
            last transition.
        message: Human-readable message indicating details about last
            transition.
    """

    type: str
    status: bool
    reason: Optional[str]
    message: Optional[str]


class SeldonV2ModelStatus(BaseModel):
    """The status of a Seldon V2 Model.

    Attributes:
        state: the current state of the Seldon V2 Model.
        description: a human-readable description of the current state.
        replicas: the current number of running pod replicas
        address: the address where the Seldon V2 Model API can be accessed.
        conditions: the list of Kubernetes conditions for the Seldon V2 Model.
    """

    state: SeldonV2ModelStatusState = SeldonV2ModelStatusState.UNKNOWN
    description: Optional[str]
    replicas: Optional[int]
    address: Optional[SeldonV2ModelStatusAddress]
    conditions: List[SeldonV2ModelStatusCondition]

    class Config:
        """Pydantic configuration class."""

        # validate attribute assignments
        validate_assignment = True
        # Ignore extra attributes from the CRD that are not reflected here
        extra = "ignore"


class SeldonV2Model(BaseModel):
    """A Seldon Core V2 model CRD.

    This is a Pydantic representation of some of the fields in the Seldon Core
    CRD (documented here:
    https://docs.seldon.io/projects/seldon-core/en/latest/reference/seldon-model.html).

    Note that not all fields are represented, only those that are relevant to
    the ZenML integration. The fields that are not represented are silently
    ignored when the Seldon V2 Model is created or updated from an external
    SeldonV2Model CRD representation.

    Attributes:
        kind: Kubernetes kind field.
        apiVersion: Kubernetes apiVersion field.
        metadata: Kubernetes metadata field.
        spec: Seldon V2 Model spec entry.
        status: Seldon V2 Model status.
    """

    kind: str = Field(SELDON_V2_MODEL_KIND, const=True)
    apiVersion: str = Field(SELDON_V2_API_VERSION, const=True)
    metadata: SeldonV2ModelMetadata
    spec: SeldonV2ModelSpec
    status: Optional[SeldonV2ModelStatus] = None

    def __str__(self) -> str:
        """Returns a string representation of the Seldon V2 Model.

        Returns:
            A string representation of the Seldon V2 Model.
        """
        return json.dumps(self.dict(exclude_none=True), indent=4)

    @classmethod
    def build(
        cls,
        name: str,
        model_uri: Optional[str] = None,
        requirements: Optional[List[str]] = None,
        parameters: Optional[List[SeldonV2ModelParameter]] = None,
        secret_name: Optional[str] = None,
        replicas: Optional[int] = None,
        memory: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
    ) -> "SeldonV2Model":
        """Build a basic Seldon V2 Model object.

        Args:
            name: The name of the Seldon V2 Model. If not explicitly passed,
                a unique name is autogenerated.
            model_uri: The storage URI for the model.
            parameters: The predictor graph parameters.
            requirements: The requirements for the model.
            secret_name: The name of the Kubernetes secret containing
                environment variable values (e.g. with credentials for the
                artifact store) to use with the model service.
            replicas: The number of replicas to use for the model service.
            memory: The memory to use for the model service.
            labels: A dictionary of labels to apply to the Seldon V2 Model.
            annotations: A dictionary of annotations to apply to the Seldon
                V2 Model.

        Returns:
            A minimal SeldonV2Model object built from the provided
            parameters.
        """
        if not name:
            name = f"zenml-{time.time()}"

        if labels is None:
            labels = {}
        if annotations is None:
            annotations = {}

        return SeldonV2Model(
            metadata=SeldonV2ModelMetadata(
                name=name, labels=labels, annotations=annotations
            ),
            spec=SeldonV2ModelSpec(
                storage_uri=model_uri,
                requirements=requirements,
                parameters=parameters,
                secret_name=secret_name,
                replicas=replicas,
                memory=memory,
            ),
        )

    def is_managed_by_zenml(self) -> bool:
        """Checks if this Seldon V2 Model is managed by ZenML.

        The convention used to differentiate between SeldonV2Model instances
        that are managed by ZenML and those that are not is to set the `app`
        label value to `zenml`.

        Returns:
            True if the Seldon V2 Model is managed by ZenML, False
            otherwise.
        """
        return self.metadata.labels.get("app") == "zenml"

    def mark_as_managed_by_zenml(self) -> None:
        """Marks this Seldon V2 Model as managed by ZenML.

        The convention used to differentiate between SeldonV2Model instances
        that are managed by ZenML and those that are not is to set the `app`
        label value to `zenml`.
        """
        self.metadata.labels["app"] = "zenml"

    @property
    def name(self) -> str:
        """Returns the name of this Seldon V2 Model.

        This is just a shortcut for `self.metadata.name`.

        Returns:
            The name of this Seldon V2 Model.
        """
        return self.metadata.name

    @property
    def state(self) -> SeldonV2ModelStatusState:
        """The state of the Seldon V2 Model.

        Returns:
            The state of the Seldon V2 Model.
        """
        if not self.status:
            return SeldonV2ModelStatusState.UNKNOWN
        return self.status.state

    def is_pending(self) -> bool:
        """Checks if the Seldon V2 Model is in a pending state.

        Returns:
            True if the Seldon V2 Model is pending, False otherwise.
        """
        return self.state == SeldonV2ModelStatusState.CREATING

    def is_available(self) -> bool:
        """Checks if the Seldon V2 Model is in an available state.

        Returns:
            True if the Seldon V2 Model is available, False otherwise.
        """
        return self.state == SeldonV2ModelStatusState.AVAILABLE

    def is_failed(self) -> bool:
        """Checks if the Seldon V2 Model is in a failed state.

        Returns:
            True if the Seldon V2 Model is failed, False otherwise.
        """
        return self.state == SeldonV2ModelStatusState.FAILED

    def get_error(self) -> Optional[str]:
        """Get a message describing the error, if in an error state.

        Returns:
            A message describing the error, if in an error state, otherwise
            None.
        """
        if self.status and self.is_failed():
            return self.status.description
        return None

    def get_pending_message(self) -> Optional[str]:
        """Get a message describing the pending conditions of the Seldon V2 Model.

        Returns:
            A message describing the pending condition of the Seldon
            V2 Model, or None, if no conditions are pending.
        """
        if not self.status or not self.status.conditions:
            return None
        ready_condition_message = [
            c.message
            for c in self.status.conditions
            if c.type == "Ready" and not c.status
        ]
        if not ready_condition_message:
            return None
        return ready_condition_message[0]

    class Config:
        """Pydantic configuration class."""

        # validate attribute assignments
        validate_assignment = True
        # Ignore extra attributes from the CRD that are not reflected here
        extra = "ignore"


class SeldonV2ClientError(Exception):
    """Base exception class for all exceptions raised by the SeldonV2Client."""


class SeldonV2ClientTimeout(SeldonV2ClientError):
    """Raised when the Seldon V2 client timed out while waiting for a resource to reach the expected status."""


class SeldonV2ModelExistsError(SeldonV2ClientError):
    """Raised when a SeldonV2Model resource cannot be created because a resource with the same name already exists."""


class SeldonV2ModelNotFoundError(SeldonV2ClientError):
    """Raised when a particular SeldonV2Model resource is not found or is not managed by ZenML."""


class SeldonV2Client:
    """A client for interacting with Seldon V2."""

    def __init__(
        self,
        context: Optional[str],
        namespace: Optional[str],
        kube_client: Optional[k8s_client.ApiClient] = None,
    ):
        """Initialize a Seldon Core V2 client.

        Args:
            context: the Kubernetes context to use.
            namespace: the Kubernetes namespace to use.
            kube_client: a Kubernetes client to use.
        """
        self._namespace = namespace
        self._initialize_k8s_clients(context=context, kube_client=kube_client)

    def _initialize_k8s_clients(
        self,
        context: Optional[str],
        kube_client: Optional[k8s_client.ApiClient] = None,
    ) -> None:
        """Initialize the Kubernetes clients.

        Args:
            context: a Kubernetes configuratino context to use.
            kube_client: a Kubernetes client to use.

        Raises:
            SeldonClientError: if Kubernetes configuration could not be loaded
        """
        if kube_client:
            # Initialize the Seldon client using the provided Kubernetes
            # client, if supplied.
            self._core_api = k8s_client.CoreV1Api(kube_client)
            self._custom_objects_api = k8s_client.CustomObjectsApi(kube_client)
            return

        try:
            k8s_config.load_incluster_config()
            if not self._namespace:
                # load the namespace in the context of which the
                # current pod is running
                self._namespace = open(
                    "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
                ).read()
        except k8s_config.config_exception.ConfigException:
            if not self._namespace:
                raise SeldonV2ClientError(
                    "The Kubernetes namespace must be explicitly "
                    "configured when running outside of a cluster."
                )
            try:
                k8s_config.load_kube_config(
                    context=context, persist_config=False
                )
            except k8s_config.config_exception.ConfigException as e:
                raise SeldonV2ClientError(
                    "Could not load the Kubernetes configuration"
                ) from e
        self._core_api = k8s_client.CoreV1Api()
        self._custom_objects_api = k8s_client.CustomObjectsApi()

    @staticmethod
    def sanitize_labels(labels: Dict[str, str]) -> None:
        """Update the label values to be valid Kubernetes labels.

        See:
        https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/#syntax-and-character-set

        Args:
            labels: the labels to sanitize.
        """
        for key, value in labels.items():
            # Kubernetes labels must be alphanumeric, no longer than
            # 63 characters, and must begin and end with an alphanumeric
            # character ([a-z0-9A-Z])
            labels[key] = re.sub(r"[^0-9a-zA-Z-_\.]+", "_", value)[:63].strip(
                "-_."
            )

    @property
    def namespace(self) -> str:
        """Returns the Kubernetes namespace in use by the client.

        Returns:
            The Kubernetes namespace in use by the client.

        Raises:
            RuntimeError: if the namespace has not been configured.
        """
        if not self._namespace:
            # shouldn't happen if the client is initialized, but we need to
            # appease the mypy type checker
            raise RuntimeError("The Kubernetes namespace is not configured")
        return self._namespace

    def create_model(
        self,
        model: SeldonV2Model,
        poll_timeout: int = 0,
    ) -> SeldonV2Model:
        """Create a Seldon Core V2 model resource.

        Args:
            model: the Seldon Core V2 model resource to create
            poll_timeout: the maximum time to wait for the model to become
                available or to fail. If set to 0, the function will return
                immediately without checking the model status. If a timeout
                occurs and the model is still pending creation, it will
                be returned anyway and no exception will be raised.

        Returns:
            the created Seldon Core V2 model resource with updated status.

        Raises:
            SeldonV2ModelExistsError: if a model with the same name
                already exists.
            SeldonV2ClientError: if an unknown error occurs during the creation of
                the model.
        """
        try:
            logger.debug(f"Creating SeldonV2model resource: {model}")

            # mark the model as managed by ZenML, to differentiate
            # between models that are created by ZenML and those that
            # are not
            model.mark_as_managed_by_zenml()

            body_deploy = model.dict(exclude_none=True)
            response = (
                self._custom_objects_api.create_namespaced_custom_object(
                    group="mlops.seldon.io",
                    version="v1alpha1",
                    namespace=self._namespace,
                    plural="models",
                    body=body_deploy,
                    _request_timeout=poll_timeout or None,
                )
            )
            logger.debug("Seldon Core V2 API response: %s", response)
        except k8s_client.rest.ApiException as e:
            logger.error(
                "Exception when creating SeldonV2Model resource: %s", str(e)
            )
            if e.status == 409:
                raise SeldonV2ModelExistsError(
                    f"A model with the name {model.name} "
                    f"already exists in namespace {self._namespace}"
                )
            raise SeldonV2ClientError(
                "Exception when creating SeldonV2Model resource"
            ) from e

        created_model = self.get_model(name=model.name)

        while poll_timeout > 0 and created_model.is_pending():
            time.sleep(5)
            poll_timeout -= 5
            created_model = self.get_model(name=model.name)

        return created_model

    def delete_model(
        self,
        name: str,
        force: bool = False,
        poll_timeout: int = 0,
    ) -> None:
        """Delete a Seldon Core V2 model resource managed by ZenML.

        Args:
            name: the name of the Seldon Core V2 model resource to delete.
            force: if True, the model deletion will be forced (the graceful
                period will be set to zero).
            poll_timeout: the maximum time to wait for the model to be
                deleted. If set to 0, the function will return immediately
                without checking the model status. If a timeout
                occurs and the model still exists, this method will
                return and no exception will be raised.

        Raises:
            SeldonClientError: if an unknown error occurs during the model
                removal.
        """
        try:
            logger.debug(f"Deleting SeldonV2Model resource: {name}")

            # call `get_model` to check that the model exists
            # and is managed by ZenML. It will raise
            # a SeldonV2ModelNotFoundError otherwise
            self.get_model(name=name)

            response = (
                self._custom_objects_api.delete_namespaced_custom_object(
                    group="mlops.seldon.io",
                    version="v1alpha1",
                    namespace=self._namespace,
                    plural="models",
                    name=name,
                    _request_timeout=poll_timeout or None,
                    grace_period_seconds=0 if force else None,
                )
            )
            logger.debug("Seldon Core V2 API response: %s", response)
        except k8s_client.rest.ApiException as e:
            logger.error(
                "Exception when deleting SeldonV2Model resource %s: %s",
                name,
                str(e),
            )
            raise SeldonV2ClientError(
                f"Exception when deleting SeldonV2Model resource {name}"
            ) from e

        while poll_timeout > 0:
            try:
                self.get_model(name=name)
            except SeldonV2ModelNotFoundError:
                return
            time.sleep(5)
            poll_timeout -= 5

    def update_model(
        self,
        model: SeldonV2Model,
        poll_timeout: int = 0,
    ) -> SeldonV2Model:
        """Update a Seldon Core V2 Model resource.

        Args:
            model: the Seldon Core V2 model resource to update
            poll_timeout: the maximum time to wait for the model to become
                available or to fail. If set to 0, the function will return
                immediately without checking the model status. If a timeout
                occurs and the model is still pending creation, it will
                be returned anyway and no exception will be raised.

        Returns:
            the updated Seldon Core V2 model resource with updated status.

        Raises:
            SeldonV2ClientError: if an unknown error occurs while updating the
                model.
        """
        try:
            logger.debug(f"Updating SeldonV2Model resource: {model.name}")

            # mark the model as managed by ZenML, to differentiate
            # between models that are created by ZenML and those that
            # are not
            model.mark_as_managed_by_zenml()

            # call `get_model` to check that the model exists
            # and is managed by ZenML. It will raise
            # a SeldonV2ModelNotFoundError otherwise
            self.get_model(name=model.name)

            response = self._custom_objects_api.patch_namespaced_custom_object(
                group="mlops.seldon.io",
                version="v1alpha1",
                namespace=self._namespace,
                plural="models",
                name=model.name,
                body=model.dict(exclude_none=True),
                _request_timeout=poll_timeout or None,
            )
            logger.debug("Seldon Core V2 API response: %s", response)
        except k8s_client.rest.ApiException as e:
            logger.error(
                "Exception when updating SeldonV2Model resource: %s", str(e)
            )
            raise SeldonV2ClientError(
                "Exception when creating SeldonV2Model resource"
            ) from e

        updated_model = self.get_model(name=model.name)

        while poll_timeout > 0 and updated_model.is_pending():
            time.sleep(5)
            poll_timeout -= 5
            updated_model = self.get_model(name=model.name)

        return updated_model

    def get_model(self, name: str) -> SeldonV2Model:
        """Get a ZenML managed Seldon Core V2 model resource by name.

        Args:
            name: the name of the Seldon Core V2 model resource to fetch.

        Returns:
            The Seldon Core V2 model resource.

        Raises:
            SeldonV2ModelNotFoundError: if the model resource cannot
                be found or is not managed by ZenML.
            SeldonV2ClientError: if an unknown error occurs while fetching
                the model.
        """
        try:
            logger.debug(f"Retrieving SeldonV2Model resource: {name}")

            response = self._custom_objects_api.get_namespaced_custom_object(
                group="mlops.seldon.io",
                version="v1alpha1",
                namespace=self._namespace,
                plural="models",
                name=name,
            )
            logger.debug("Seldon Core V2 API response: %s", response)
            try:
                model = SeldonV2Model(**response)
            except ValidationError as e:
                logger.error(
                    "Invalid Seldon Core V2 model resource: %s\n%s",
                    str(e),
                    str(response),
                )
                raise SeldonV2ModelNotFoundError(
                    f"SeldonV2Model resource {name} could not be parsed"
                )

            # Only Seldon models managed by ZenML are returned
            if not model.is_managed_by_zenml():
                raise SeldonV2ModelNotFoundError(
                    f"Seldon V2 model {name} is not managed by ZenML"
                )
            return model

        except k8s_client.rest.ApiException as e:
            if e.status == 404:
                raise SeldonV2ModelNotFoundError(
                    f"SeldonV2Model resource not found: {name}"
                ) from e
            logger.error(
                "Exception when fetching SeldonV2Model resource %s: %s",
                name,
                str(e),
            )
            raise SeldonV2ClientError(
                f"Unexpected exception when fetching SeldonV2Model "
                f"resource: {name}"
            ) from e

    def find_models(
        self,
        name: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        fields: Optional[Dict[str, str]] = None,
    ) -> List[SeldonV2Model]:
        """Find all ZenML-managed Seldon Core V2 model resources matching the given criteria.

        Args:
            name: optional name of the model resource to find.
            fields: optional selector to restrict the list of returned
                Seldon V2 models by their fields. Defaults to everything.
            labels: optional selector to restrict the list of returned
                Seldon V2 models by their labels. Defaults to everything.

        Returns:
            List of Seldon Core V2 models that match the given criteria.

        Raises:
            SeldonV2ClientError: if an unknown error occurs while fetching
                the models.
        """
        fields = fields or {}
        labels = labels or {}
        # always filter results to only include Seldon V2 models managed
        # by ZenML
        labels["app"] = "zenml"
        if name:
            fields = {"metadata.name": name}
        field_selector = (
            ",".join(f"{k}={v}" for k, v in fields.items()) if fields else None
        )
        label_selector = (
            ",".join(f"{k}={v}" for k, v in labels.items()) if labels else None
        )
        try:
            logger.debug(
                f"Searching SeldonV2Model resources with label selector "
                f"'{labels or ''}' and field selector '{fields or ''}'"
            )
            response = self._custom_objects_api.list_namespaced_custom_object(
                group="mlops.seldon.io",
                version="v1alpha1",
                namespace=self._namespace,
                plural="models",
                field_selector=field_selector,
                label_selector=label_selector,
            )
            logger.debug(
                "Seldon Core V2 API returned %s items", len(response["items"])
            )
            models = []
            for item in response.get("items") or []:
                try:
                    models.append(SeldonV2Model(**item))
                except ValidationError as e:
                    logger.error(
                        "Invalid Seldon Core V2 model resource: %s\n%s",
                        str(e),
                        str(item),
                    )
            return models
        except k8s_client.rest.ApiException as e:
            logger.error(
                "Exception when searching SeldonV2Model resources with "
                "label selector '%s' and field selector '%s': %s",
                label_selector or "",
                field_selector or "",
            )
            raise SeldonV2ClientError(
                f"Unexpected exception when searching SeldonV2Model "
                f"with labels '{labels or ''}' and field '{fields or ''}'"
            ) from e

    def get_model_logs(
        self,
        name: str,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Get the logs of a Seldon Core V2 model resource.

        Args:
            name: the name of the Seldon Core V2 model to get logs for.
            follow: if True, the logs will be streamed as they are written
            tail: only retrieve the last NUM lines of log output.

        Returns:
            A generator that can be accessed to get the service logs.

        Yields:
            The next log line.

        Raises:
            SeldonClientError: if an unknown error occurs while fetching
                the logs.
        """
        logger.debug(f"Retrieving logs for SeldonV2Model resource: {name}")
        try:
            response = self._core_api.list_namespaced_pod(
                namespace=self._namespace,
                label_selector=f"seldon-model-id={name}",
            )
            logger.debug("Kubernetes API response: %s", response)
            pods = response.items
            if not pods:
                raise SeldonV2ClientError(
                    f"The Seldon Core V2 model {name} is not currently "
                    f"running: no Kubernetes pods associated with it were found"
                )
            pod = pods[0]
            pod_name = pod.metadata.name

            containers = [c.name for c in pod.spec.containers]
            init_containers = [c.name for c in pod.spec.init_containers]
            container_statuses = {
                c.name: c.started or c.restart_count
                for c in pod.status.container_statuses
            }

            container = "default"
            if container not in containers:
                container = containers[0]
            # some containers might not be running yet and have no logs to show,
            # so we need to filter them out
            if not container_statuses[container]:
                container = init_containers[0]

            logger.info(
                f"Retrieving logs for pod: `{pod_name}` and container "
                f"`{container}` in namespace `{self._namespace}`"
            )
            response = self._core_api.read_namespaced_pod_log(
                name=pod_name,
                namespace=self._namespace,
                container=container,
                follow=follow,
                tail_lines=tail,
                _preload_content=False,
            )
        except k8s_client.rest.ApiException as e:
            logger.error(
                "Exception when fetching logs for SeldonV2Model resource "
                "%s: %s",
                name,
                str(e),
            )
            raise SeldonV2ClientError(
                f"Unexpected exception when fetching logs for SeldonV2Model "
                f"resource: {name}"
            ) from e

        try:
            while True:
                line = response.readline().decode("utf-8").rstrip("\n")
                if not line:
                    return
                stop = yield line
                if stop:
                    return
        finally:
            response.release_conn()

    def create_or_update_secret(
        self,
        name: str,
        secret_values: Dict[str, Any],
    ) -> None:
        """Create or update a Kubernetes Secret resource.

        Args:
            name: the name of the Secret resource to create.
            secret_values: secret key-values that should be
                stored in the Secret resource.

        Raises:
            SeldonClientError: if an unknown error occurs during the creation of
                the secret.
            k8s_client.rest.ApiException: unexpected error.
        """
        try:
            logger.debug(f"Creating Secret resource: {name}")

            secret_data = {
                k.upper(): base64.b64encode(str(v).encode("utf-8")).decode(
                    "ascii"
                )
                for k, v in secret_values.items()
                if v is not None
            }

            secret = k8s_client.V1Secret(
                metadata=k8s_client.V1ObjectMeta(
                    name=name,
                    labels={"app": "zenml"},
                ),
                type="Opaque",
                data=secret_data,
            )

            try:
                # check if the secret is already present
                self._core_api.read_namespaced_secret(
                    name=name,
                    namespace=self._namespace,
                )
                # if we got this far, the secret is already present, update it
                # in place
                response = self._core_api.replace_namespaced_secret(
                    name=name,
                    namespace=self._namespace,
                    body=secret,
                )
            except k8s_client.rest.ApiException as e:
                if e.status != 404:
                    # if an error other than 404 is raised here, treat it
                    # as an unexpected error
                    raise
                response = self._core_api.create_namespaced_secret(
                    namespace=self._namespace,
                    body=secret,
                )
            logger.debug("Kubernetes API response: %s", response)
        except k8s_client.rest.ApiException as e:
            logger.error("Exception when creating Secret resource: %s", str(e))
            raise SeldonV2ClientError(
                "Exception when creating Secret resource"
            ) from e

    def delete_secret(
        self,
        name: str,
    ) -> None:
        """Delete a Kubernetes Secret resource managed by ZenML.

        Args:
            name: the name of the Kubernetes Secret resource to delete.

        Raises:
            SeldonClientError: if an unknown error occurs during the removal
                of the secret.
        """
        try:
            logger.debug(f"Deleting Secret resource: {name}")

            response = self._core_api.delete_namespaced_secret(
                name=name,
                namespace=self._namespace,
            )
            logger.debug("Kubernetes API response: %s", response)
        except k8s_client.rest.ApiException as e:
            if e.status == 404:
                # the secret is no longer present, nothing to do
                return
            logger.error(
                "Exception when deleting Secret resource %s: %s",
                name,
                str(e),
            )
            raise SeldonV2ClientError(
                f"Exception when deleting Secret resource {name}"
            ) from e
