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

import base64
import json
import re
import time
from typing import Dict, Generator, List, Optional

from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from pydantic import BaseModel, Field, ValidationError

from zenml.logger import get_logger
from zenml.secret.base_secret import BaseSecretSchema
from zenml.utils.enum_utils import StrEnum

logger = get_logger(__name__)


SELDON_DEPLOYMENT_KIND = "SeldonDeployment"
SELDON_DEPLOYMENT_API_VERSION = "machinelearning.seldon.io/v1"


class SeldonDeploymentMetadata(BaseModel):
    """Metadata for a Seldon Deployment.

    Attributes:
        name: the name of the Seldon Deployment.
        labels: Kubernetes labels for the Seldon Deployment.
        annotations: Kubernetes annotations for the Seldon Deployment.
        creationTimestamp: the creation timestamp of the Seldon Deployment.
    """

    name: str
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)
    creationTimestamp: Optional[str]

    class Config:
        """Pydantic configuration class."""

        # validate attribute assignments
        validate_assignment = True
        # Ignore extra attributes from the CRD that are not reflected here
        extra = "ignore"


class SeldonDeploymentPredictiveUnitType(StrEnum):
    """Predictive unit types for a Seldon Deployment."""

    UNKNOWN_TYPE = "UNKNOWN_TYPE"
    ROUTER = "ROUTER"
    COMBINER = "COMBINER"
    MODEL = "MODEL"
    TRANSFORMER = "TRANSFORMER"
    OUTPUT_TRANSFORMER = "OUTPUT_TRANSFORMER"


class SeldonDeploymentPredictiveUnit(BaseModel):
    """Seldon Deployment predictive unit.

    Attributes:
        name: the name of the predictive unit.
        type: predictive unit type.
        implementation: the Seldon Core implementation used to serve the model.
        modelUri: URI of the model (or models) to serve.
        serviceAccountName: the name of the service account to associate with
            the predictive unit container.
        envSecretRefName: the name of a Kubernetes secret that contains
            environment variables (e.g. credentials) to be configured for the
            predictive unit container.
        children: a list of child predictive units that together make up the
            model serving graph.
    """

    name: str
    type: Optional[
        SeldonDeploymentPredictiveUnitType
    ] = SeldonDeploymentPredictiveUnitType.MODEL
    implementation: Optional[str]
    modelUri: Optional[str]
    serviceAccountName: Optional[str]
    envSecretRefName: Optional[str]
    children: List["SeldonDeploymentPredictiveUnit"] = Field(
        default_factory=list
    )

    class Config:
        """Pydantic configuration class."""

        # validate attribute assignments
        validate_assignment = True
        # Ignore extra attributes from the CRD that are not reflected here
        extra = "ignore"


class SeldonDeploymentPredictor(BaseModel):
    """Seldon Deployment predictor.

    Attributes:
        name: the name of the predictor.
        replicas: the number of pod replicas for the predictor.
        graph: the serving graph composed of one or more predictive units.
    """

    name: str
    replicas: int = 1
    graph: SeldonDeploymentPredictiveUnit = Field(
        default_factory=SeldonDeploymentPredictiveUnit
    )

    class Config:
        """Pydantic configuration class."""

        # validate attribute assignments
        validate_assignment = True
        # Ignore extra attributes from the CRD that are not reflected here
        extra = "ignore"


class SeldonDeploymentSpec(BaseModel):
    """Spec for a Seldon Deployment.

    Attributes:
        name: the name of the Seldon Deployment.
        protocol: the API protocol used for the Seldon Deployment.
        predictors: a list of predictors that make up the serving graph.
        replicas: the default number of pod replicas used for the predictors.
    """

    name: str
    protocol: Optional[str]
    predictors: List[SeldonDeploymentPredictor]
    replicas: int = 1

    class Config:
        """Pydantic configuration class."""

        # validate attribute assignments
        validate_assignment = True
        # Ignore extra attributes from the CRD that are not reflected here
        extra = "ignore"


class SeldonDeploymentStatusState(StrEnum):
    """Possible state values for a Seldon Deployment."""

    UNKNOWN = "Unknown"
    AVAILABLE = "Available"
    CREATING = "Creating"
    FAILED = "Failed"


class SeldonDeploymentStatusAddress(BaseModel):
    """The status address for a Seldon Deployment.

    Attributes:
        url: the URL where the Seldon Deployment API can be accessed internally.
    """

    url: str


class SeldonDeploymentStatusCondition(BaseModel):
    """The Kubernetes status condition entry for a Seldon Deployment.

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


class SeldonDeploymentStatus(BaseModel):
    """The status of a Seldon Deployment.

    Attributes:
        state: the current state of the Seldon Deployment.
        description: a human-readable description of the current state.
        replicas: the current number of running pod replicas
        address: the address where the Seldon Deployment API can be accessed.
        conditions: the list of Kubernetes conditions for the Seldon Deployment.
    """

    state: SeldonDeploymentStatusState = SeldonDeploymentStatusState.UNKNOWN
    description: Optional[str]
    replicas: Optional[int]
    address: Optional[SeldonDeploymentStatusAddress]
    conditions: List[SeldonDeploymentStatusCondition]

    class Config:
        """Pydantic configuration class."""

        # validate attribute assignments
        validate_assignment = True
        # Ignore extra attributes from the CRD that are not reflected here
        extra = "ignore"


class SeldonDeployment(BaseModel):
    """A Seldon Core deployment CRD.

    This is a Pydantic representation of some of the fields in the Seldon Core
    CRD (documented here:
    https://docs.seldon.io/projects/seldon-core/en/latest/reference/seldon-deployment.html).

    Note that not all fields are represented, only those that are relevant to
    the ZenML integration. The fields that are not represented are silently
    ignored when the Seldon Deployment is created or updated from an external
    SeldonDeployment CRD representation.

    Attributes:
        kind: Kubernetes kind field.
        apiVersion: Kubernetes apiVersion field.
        metadata: Kubernetes metadata field.
        spec: Seldon Deployment spec entry.
        status: Seldon Deployment status.
    """

    kind: str = Field(SELDON_DEPLOYMENT_KIND, const=True)
    apiVersion: str = Field(SELDON_DEPLOYMENT_API_VERSION, const=True)
    metadata: SeldonDeploymentMetadata = Field(
        default_factory=SeldonDeploymentMetadata
    )
    spec: SeldonDeploymentSpec = Field(default_factory=SeldonDeploymentSpec)
    status: Optional[SeldonDeploymentStatus]

    def __str__(self) -> str:
        return json.dumps(self.dict(exclude_none=True), indent=4)

    @classmethod
    def build(
        cls,
        name: Optional[str] = None,
        model_uri: Optional[str] = None,
        model_name: Optional[str] = None,
        implementation: Optional[str] = None,
        secret_name: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
    ) -> "SeldonDeployment":
        """Build a basic Seldon Deployment object.

        Args:
            name: The name of the Seldon Deployment. If not explicitly passed,
                a unique name is autogenerated.
            model_uri: The URI of the model.
            model_name: The name of the model.
            implementation: The implementation of the model.
            secret_name: The name of the Kubernetes secret containing
                environment variable values (e.g. with credentials for the
                artifact store) to use with the deployment service.
            labels: A dictionary of labels to apply to the Seldon Deployment.
            annotations: A dictionary of annotations to apply to the Seldon
                Deployment.

        Returns:
            A minimal SeldonDeployment object built from the provided
            parameters.
        """

        if not name:
            name = f"zenml-{time.time()}"

        if labels is None:
            labels = {}
        if annotations is None:
            annotations = {}

        return SeldonDeployment(
            metadata=SeldonDeploymentMetadata(
                name=name, labels=labels, annotations=annotations
            ),
            spec=SeldonDeploymentSpec(
                name=name,
                predictors=[
                    SeldonDeploymentPredictor(
                        name=model_name or "",
                        graph=SeldonDeploymentPredictiveUnit(
                            name="default",
                            type=SeldonDeploymentPredictiveUnitType.MODEL,
                            modelUri=model_uri or "",
                            implementation=implementation or "",
                            envSecretRefName=secret_name,
                        ),
                    )
                ],
            ),
        )

    def is_managed_by_zenml(self) -> bool:
        """Checks if this Seldon Deployment is managed by ZenML.

        The convention used to differentiate between SeldonDeployment instances
        that are managed by ZenML and those that are not is to set the `app`
        label value to `zenml`.

        Returns:
            True if the Seldon Deployment is managed by ZenML, False
            otherwise.
        """
        return self.metadata.labels.get("app") == "zenml"

    def mark_as_managed_by_zenml(self) -> None:
        """Marks this Seldon Deployment as managed by ZenML.

        The convention used to differentiate between SeldonDeployment instances
        that are managed by ZenML and those that are not is to set the `app`
        label value to `zenml`.
        """
        self.metadata.labels["app"] = "zenml"

    @property
    def name(self) -> str:
        """Returns the name of this Seldon Deployment.

        This is just a shortcut for `self.metadata.name`.

        Returns:
            The name of this Seldon Deployment.
        """
        return self.metadata.name

    @property
    def state(self) -> SeldonDeploymentStatusState:
        """The state of the Seldon Deployment.

        Returns:
            The state of the Seldon Deployment.
        """
        if not self.status:
            return SeldonDeploymentStatusState.UNKNOWN
        return self.status.state

    def is_pending(self) -> bool:
        """Checks if the Seldon Deployment is in a pending state.

        Returns:
            True if the Seldon Deployment is pending, False otherwise.
        """
        return self.state == SeldonDeploymentStatusState.CREATING

    def is_available(self) -> bool:
        """Checks if the Seldon Deployment is in an available state.

        Returns:
            True if the Seldon Deployment is available, False otherwise.
        """
        return self.state == SeldonDeploymentStatusState.AVAILABLE

    def is_failed(self) -> bool:
        """Checks if the Seldon Deployment is in a failed state.

        Returns:
            True if the Seldon Deployment is failed, False otherwise.
        """
        return self.state == SeldonDeploymentStatusState.FAILED

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
        """Get a message describing the pending conditions of the Seldon
        Deployment.

        Returns:
            A message describing the pending condition of the Seldon
            Deployment, or None, if no conditions are pending.
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


class SeldonClientError(Exception):
    """Base exception class for all exceptions raised by the SeldonClient."""


class SeldonClientTimeout(SeldonClientError):
    """Raised when the Seldon client timed out while waiting for a resource
    to reach the expected status."""


class SeldonDeploymentExistsError(SeldonClientError):
    """Raised when a SeldonDeployment resource cannot be created because a
    resource with the same name already exists."""


class SeldonDeploymentNotFoundError(SeldonClientError):
    """Raised when a particular SeldonDeployment resource is not found or is
    not managed by ZenML."""


class SeldonClient:
    def __init__(self, context: Optional[str], namespace: Optional[str]):
        """Initialize a Seldon Core client.

        Args:
            context: the Kubernetes context to use.
            namespace: the Kubernetes namespace to use.
        """
        self._context = context
        self._namespace = namespace
        self._initialize_k8s_clients()

    def _initialize_k8s_clients(self) -> None:
        """Initialize the Kubernetes clients."""
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
                raise SeldonClientError(
                    "The Kubernetes namespace must be explicitly "
                    "configured when running outside of a cluster."
                )
            try:
                k8s_config.load_kube_config(
                    context=self._context, persist_config=False
                )
            except k8s_config.config_exception.ConfigException as e:
                raise SeldonClientError(
                    "Could not load the Kubernetes configuration"
                ) from e
        self._core_api = k8s_client.CoreV1Api()
        self._custom_objects_api = k8s_client.CustomObjectsApi()

    @staticmethod
    def sanitize_labels(labels: Dict[str, str]) -> None:
        """Update the label values to be valid Kubernetes labels.

        See: https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/#syntax-and-character-set
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
        """
        if not self._namespace:
            # shouldn't happen if the client is initialized, but we need to
            # appease the mypy type checker
            raise RuntimeError("The Kubernetes namespace is not configured")
        return self._namespace

    def create_deployment(
        self,
        deployment: SeldonDeployment,
        poll_timeout: int = 0,
    ) -> SeldonDeployment:
        """Create a Seldon Core deployment resource.

        Args:
            deployment: the Seldon Core deployment resource to create
            poll_timeout: the maximum time to wait for the deployment to become
                available or to fail. If set to 0, the function will return
                immediately without checking the deployment status. If a timeout
                occurs and the deployment is still pending creation, it will
                be returned anyway and no exception will be raised.

        Returns:
            the created Seldon Core deployment resource with updated status.

        Raises:
            SeldonDeploymentExistsError: if a deployment with the same name
                already exists.
            SeldonDeploymentNotFoundError: if the newly created deployment
                resource cannot be found.
            SeldonClientError: if an unknown error occurs during the creation of
                the deployment.
        """
        try:
            logger.debug(f"Creating SeldonDeployment resource: {deployment}")

            # mark the deployment as managed by ZenML, to differentiate
            # between deployments that are created by ZenML and those that
            # are not
            deployment.mark_as_managed_by_zenml()

            response = self._custom_objects_api.create_namespaced_custom_object(
                group="machinelearning.seldon.io",
                version="v1",
                namespace=self._namespace,
                plural="seldondeployments",
                body=deployment.dict(exclude_none=True),
                _request_timeout=poll_timeout or None,
            )
            logger.debug("Seldon Core API response: %s", response)
        except k8s_client.rest.ApiException as e:
            logger.error(
                "Exception when creating SeldonDeployment resource: %s", str(e)
            )
            if e.status == 409:
                raise SeldonDeploymentExistsError(
                    f"A deployment with the name {deployment.name} "
                    f"already exists in namespace {self._namespace}"
                )
            raise SeldonClientError(
                "Exception when creating SeldonDeployment resource"
            ) from e

        created_deployment = self.get_deployment(name=deployment.name)

        while poll_timeout > 0 and created_deployment.is_pending():
            time.sleep(5)
            poll_timeout -= 5
            created_deployment = self.get_deployment(name=deployment.name)

        return created_deployment

    def delete_deployment(
        self,
        name: str,
        force: bool = False,
        poll_timeout: int = 0,
    ) -> None:
        """Delete a Seldon Core deployment resource managed by ZenML.

        Args:
            name: the name of the Seldon Core deployment resource to delete.
            force: if True, the deployment deletion will be forced (the graceful
                period will be set to zero).
            poll_timeout: the maximum time to wait for the deployment to be
                deleted. If set to 0, the function will return immediately
                without checking the deployment status. If a timeout
                occurs and the deployment still exists, this method will
                return and no exception will be raised.

        Raises:
            SeldonDeploymentNotFoundError: if the deployment resource cannot be
                found or is not managed by ZenML.
            SeldonClientError: if an unknown error occurs during the deployment
                removal.
        """
        try:
            logger.debug(f"Deleting SeldonDeployment resource: {name}")

            # call `get_deployment` to check that the deployment exists
            # and is managed by ZenML. It will raise
            # a SeldonDeploymentNotFoundError otherwise
            self.get_deployment(name=name)

            response = self._custom_objects_api.delete_namespaced_custom_object(
                group="machinelearning.seldon.io",
                version="v1",
                namespace=self._namespace,
                plural="seldondeployments",
                name=name,
                _request_timeout=poll_timeout or None,
                grace_period_seconds=0 if force else None,
            )
            logger.debug("Seldon Core API response: %s", response)
        except k8s_client.rest.ApiException as e:
            logger.error(
                "Exception when deleting SeldonDeployment resource %s: %s",
                name,
                str(e),
            )
            raise SeldonClientError(
                f"Exception when deleting SeldonDeployment resource {name}"
            ) from e

        while poll_timeout > 0:
            try:
                self.get_deployment(name=name)
            except SeldonDeploymentNotFoundError:
                return
            time.sleep(5)
            poll_timeout -= 5

    def update_deployment(
        self,
        deployment: SeldonDeployment,
        poll_timeout: int = 0,
    ) -> SeldonDeployment:
        """Update a Seldon Core deployment resource.

        Args:
            deployment: the Seldon Core deployment resource to update
            poll_timeout: the maximum time to wait for the deployment to become
                available or to fail. If set to 0, the function will return
                immediately without checking the deployment status. If a timeout
                occurs and the deployment is still pending creation, it will
                be returned anyway and no exception will be raised.

        Returns:
            the updated Seldon Core deployment resource with updated status.

        Raises:
            SeldonDeploymentNotFoundError: if deployment resource with the given
                name cannot be found.
            SeldonClientError: if an unknown error occurs while updating the
                deployment.
        """
        try:
            logger.debug(
                f"Updating SeldonDeployment resource: {deployment.name}"
            )

            # mark the deployment as managed by ZenML, to differentiate
            # between deployments that are created by ZenML and those that
            # are not
            deployment.mark_as_managed_by_zenml()

            # call `get_deployment` to check that the deployment exists
            # and is managed by ZenML. It will raise
            # a SeldonDeploymentNotFoundError otherwise
            self.get_deployment(name=deployment.name)

            response = self._custom_objects_api.patch_namespaced_custom_object(
                group="machinelearning.seldon.io",
                version="v1",
                namespace=self._namespace,
                plural="seldondeployments",
                name=deployment.name,
                body=deployment.dict(exclude_none=True),
                _request_timeout=poll_timeout or None,
            )
            logger.debug("Seldon Core API response: %s", response)
        except k8s_client.rest.ApiException as e:
            logger.error(
                "Exception when updating SeldonDeployment resource: %s", str(e)
            )
            raise SeldonClientError(
                "Exception when creating SeldonDeployment resource"
            ) from e

        updated_deployment = self.get_deployment(name=deployment.name)

        while poll_timeout > 0 and updated_deployment.is_pending():
            time.sleep(5)
            poll_timeout -= 5
            updated_deployment = self.get_deployment(name=deployment.name)

        return updated_deployment

    def get_deployment(self, name: str) -> SeldonDeployment:
        """Get a ZenML managed Seldon Core deployment resource by name.

        Args:
            name: the name of the Seldon Core deployment resource to fetch.

        Returns:
            The Seldon Core deployment resource.

        Raises:
            SeldonDeploymentNotFoundError: if the deployment resource cannot
                be found or is not managed by ZenML.
            SeldonClientError: if an unknown error occurs while fetching
                the deployment.
        """

        try:
            logger.debug(f"Retrieving SeldonDeployment resource: {name}")

            response = self._custom_objects_api.get_namespaced_custom_object(
                group="machinelearning.seldon.io",
                version="v1",
                namespace=self._namespace,
                plural="seldondeployments",
                name=name,
            )
            logger.debug("Seldon Core API response: %s", response)
            try:
                deployment = SeldonDeployment(**response)
            except ValidationError as e:
                logger.error(
                    "Invalid Seldon Core deployment resource: %s\n%s",
                    str(e),
                    str(response),
                )
                raise SeldonDeploymentNotFoundError(
                    f"SeldonDeployment resource {name} could not be parsed"
                )

            # Only Seldon deployments managed by ZenML are returned
            if not deployment.is_managed_by_zenml():
                raise SeldonDeploymentNotFoundError(
                    f"Seldon Deployment {name} is not managed by ZenML"
                )
            return deployment

        except k8s_client.rest.ApiException as e:
            if e.status == 404:
                raise SeldonDeploymentNotFoundError(
                    f"SeldonDeployment resource not found: {name}"
                ) from e
            logger.error(
                "Exception when fetching SeldonDeployment resource %s: %s",
                name,
                str(e),
            )
            raise SeldonClientError(
                f"Unexpected exception when fetching SeldonDeployment "
                f"resource: {name}"
            ) from e

    def find_deployments(
        self,
        name: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        fields: Optional[Dict[str, str]] = None,
    ) -> List[SeldonDeployment]:
        """Find all ZenML managed Seldon Core deployment resources that match
        the given criteria.

        Args:
            name: optional name of the deployment resource to find.
            fields: optional selector to restrict the list of returned
                Seldon deployments by their fields. Defaults to everything.
            labels: optional selector to restrict the list of returned
                Seldon deployments by their labels. Defaults to everything.

        Returns:
            List of Seldon Core deployments that match the given criteria.

        Raises:
            SeldonClientError: if an unknown error occurs while fetching
                the deployments.
        """
        fields = fields or {}
        labels = labels or {}
        # always filter results to only include Seldon deployments managed
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
                f"Searching SeldonDeployment resources with label selector "
                f"'{labels or ''}' and field selector '{fields or ''}'"
            )
            response = self._custom_objects_api.list_namespaced_custom_object(
                group="machinelearning.seldon.io",
                version="v1",
                namespace=self._namespace,
                plural="seldondeployments",
                field_selector=field_selector,
                label_selector=label_selector,
            )
            logger.debug(
                "Seldon Core API returned %s items", len(response["items"])
            )
            deployments = []
            for item in response.get("items") or []:
                try:
                    deployments.append(SeldonDeployment(**item))
                except ValidationError as e:
                    logger.error(
                        "Invalid Seldon Core deployment resource: %s\n%s",
                        str(e),
                        str(item),
                    )
            return deployments
        except k8s_client.rest.ApiException as e:
            logger.error(
                "Exception when searching SeldonDeployment resources with "
                "label selector '%s' and field selector '%s': %s",
                label_selector or "",
                field_selector or "",
            )
            raise SeldonClientError(
                f"Unexpected exception when searching SeldonDeployment "
                f"with labels '{labels or ''}' and field '{fields or ''}'"
            ) from e

    def get_deployment_logs(
        self,
        name: str,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Get the logs of a Seldon Core deployment resource.

        Args:
            name: the name of the Seldon Core deployment to get logs for.
            follow: if True, the logs will be streamed as they are written
            tail: only retrieve the last NUM lines of log output.

        Returns:
            A generator that can be acccessed to get the service logs.

        Raises:
            SeldonClientError: if an unknown error occurs while fetching
                the logs.
        """
        logger.debug(f"Retrieving logs for SeldonDeployment resource: {name}")
        try:
            response = self._core_api.list_namespaced_pod(
                namespace=self._namespace,
                label_selector=f"seldon-deployment-id={name}",
            )
            logger.debug("Kubernetes API response: %s", response)
            pods = response.items
            if not pods:
                raise SeldonClientError(
                    f"The Seldon Core deployment {name} is not currently "
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
                "Exception when fetching logs for SeldonDeployment resource "
                "%s: %s",
                name,
                str(e),
            )
            raise SeldonClientError(
                f"Unexpected exception when fetching logs for SeldonDeployment "
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
        secret: BaseSecretSchema,
    ) -> None:
        """Create or update a Kubernetes Secret resource with the information
        contained in a ZenML secret.

        Args:
            name: the name of the Secret resource to create.
            secret: a ZenML secret with key-values that should be
                stored in the Secret resource.

        Raises:
            SeldonClientError: if an unknown error occurs during the creation of
                the secret.
        """
        try:
            logger.debug(f"Creating Secret resource: {name}")

            secret_data = {
                k.upper(): base64.b64encode(str(v).encode("utf-8")).decode(
                    "ascii"
                )
                for k, v in secret.content.items()
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
            raise SeldonClientError(
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
            raise SeldonClientError(
                f"Exception when deleting Secret resource {name}"
            ) from e
