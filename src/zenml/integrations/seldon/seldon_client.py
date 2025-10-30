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
"""Implementation of the Seldon client for ZenML."""

import base64
import json
import re
import time
from typing import Any, Literal
from collections.abc import Generator

from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from zenml.logger import get_logger
from zenml.utils.enum_utils import StrEnum

logger = get_logger(__name__)

api = k8s_client.ApiClient()


class SeldonDeploymentPredictorParameter(BaseModel):
    """Parameter for Seldon Deployment predictor.

    Attributes:
        name: parameter name
        type: parameter, can be INT, FLOAT, DOUBLE, STRING, BOOL
        value: parameter value
    """

    name: str = ""
    type: str = ""
    value: str = ""
    model_config = ConfigDict(
        # validate attribute assignments
        validate_assignment=True,
        # Ignore extra attributes from the CRD that are not reflected here
        extra="ignore",
    )


class SeldonResourceRequirements(BaseModel):
    """Resource requirements for a Seldon deployed model.

    Attributes:
        limits: an upper limit of resources to be used by the model
        requests: resources requested by the model
    """

    limits: dict[str, str] = Field(default_factory=dict)
    requests: dict[str, str] = Field(default_factory=dict)


class SeldonDeploymentMetadata(BaseModel):
    """Metadata for a Seldon Deployment.

    Attributes:
        name: the name of the Seldon Deployment.
        labels: Kubernetes labels for the Seldon Deployment.
        annotations: Kubernetes annotations for the Seldon Deployment.
        creationTimestamp: the creation timestamp of the Seldon Deployment.
    """

    name: str
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    creationTimestamp: str | None = None
    model_config = ConfigDict(
        # validate attribute assignments
        validate_assignment=True,
        # Ignore extra attributes from the CRD that are not reflected here
        extra="ignore",
    )


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
    type: SeldonDeploymentPredictiveUnitType | None = (
        SeldonDeploymentPredictiveUnitType.MODEL
    )
    implementation: str | None = None
    modelUri: str | None = None
    parameters: list[SeldonDeploymentPredictorParameter] | None = None
    serviceAccountName: str | None = None
    envSecretRefName: str | None = None
    children: list["SeldonDeploymentPredictiveUnit"] | None = None
    model_config = ConfigDict(
        # validate attribute assignments
        validate_assignment=True,
        # Ignore extra attributes from the CRD that are not reflected here
        extra="ignore",
    )


class SeldonDeploymentComponentSpecs(BaseModel):
    """Component specs for a Seldon Deployment.

    Attributes:
        spec: the component spec.
    """

    spec: dict[str, Any] | None = None
    model_config = ConfigDict(
        # validate attribute assignments
        validate_assignment=True,
        # Ignore extra attributes from the CRD that are not reflected here
        extra="ignore",
    )


class SeldonDeploymentPredictor(BaseModel):
    """Seldon Deployment predictor.

    Attributes:
        name: the name of the predictor.
        replicas: the number of pod replicas for the predictor.
        graph: the serving graph composed of one or more predictive units.
    """

    name: str
    replicas: int = 1
    graph: SeldonDeploymentPredictiveUnit
    engineResources: SeldonResourceRequirements | None = Field(
        default_factory=SeldonResourceRequirements
    )
    componentSpecs: list[SeldonDeploymentComponentSpecs] | None = None
    model_config = ConfigDict(
        # validate attribute assignments
        validate_assignment=True,
        # Ignore extra attributes from the CRD that are not reflected here
        extra="ignore",
    )


class SeldonDeploymentSpec(BaseModel):
    """Spec for a Seldon Deployment.

    Attributes:
        name: the name of the Seldon Deployment.
        protocol: the API protocol used for the Seldon Deployment.
        predictors: a list of predictors that make up the serving graph.
        replicas: the default number of pod replicas used for the predictors.
    """

    name: str
    protocol: str | None = None
    predictors: list[SeldonDeploymentPredictor]
    replicas: int = 1
    model_config = ConfigDict(
        # validate attribute assignments
        validate_assignment=True,
        # Ignore extra attributes from the CRD that are not reflected here
        extra="ignore",
    )


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
    reason: str | None = None
    message: str | None = None


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
    description: str | None = None
    replicas: int | None = None
    address: SeldonDeploymentStatusAddress | None = None
    conditions: list[SeldonDeploymentStatusCondition]
    model_config = ConfigDict(
        # validate attribute assignments
        validate_assignment=True,
        # Ignore extra attributes from the CRD that are not reflected here
        extra="ignore",
    )


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

    kind: Literal["SeldonDeployment"] = "SeldonDeployment"
    apiVersion: Literal["machinelearning.seldon.io/v1"] = (
        "machinelearning.seldon.io/v1"
    )
    metadata: SeldonDeploymentMetadata
    spec: SeldonDeploymentSpec
    status: SeldonDeploymentStatus | None = None

    def __str__(self) -> str:
        """Returns a string representation of the Seldon Deployment.

        Returns:
            A string representation of the Seldon Deployment.
        """
        return json.dumps(self.model_dump(exclude_none=True), indent=4)

    @classmethod
    def build(
        cls,
        name: str | None = None,
        model_uri: str | None = None,
        model_name: str | None = None,
        implementation: str | None = None,
        parameters: list[SeldonDeploymentPredictorParameter] | None = None,
        engineResources: SeldonResourceRequirements | None = None,
        secret_name: str | None = None,
        labels: dict[str, str] | None = None,
        annotations: dict[str, str] | None = None,
        is_custom_deployment: bool | None = False,
        spec: dict[Any, Any] | None = None,
        serviceAccountName: str | None = None,
    ) -> "SeldonDeployment":
        """Build a basic Seldon Deployment object.

        Args:
            name: The name of the Seldon Deployment. If not explicitly passed,
                a unique name is autogenerated.
            model_uri: The URI of the model.
            model_name: The name of the model.
            implementation: The implementation of the model.
            parameters: The predictor graph parameters.
            engineResources: The resources to be allocated to the model.
            secret_name: The name of the Kubernetes secret containing
                environment variable values (e.g. with credentials for the
                artifact store) to use with the deployment service.
            labels: A dictionary of labels to apply to the Seldon Deployment.
            annotations: A dictionary of annotations to apply to the Seldon
                Deployment.
            spec: A Kubernetes pod spec to use for the Seldon Deployment.
            is_custom_deployment: Whether the Seldon Deployment is a custom
                or a built-in one.
            serviceAccountName: The name of the service account to associate
                with the predictive unit container.

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

        if is_custom_deployment:
            predictors = [
                SeldonDeploymentPredictor(
                    name=model_name or "",
                    graph=SeldonDeploymentPredictiveUnit(
                        name="classifier",
                        type=SeldonDeploymentPredictiveUnitType.MODEL,
                        parameters=parameters,
                        serviceAccountName=serviceAccountName,
                    ),
                    engineResources=engineResources,
                    componentSpecs=[
                        SeldonDeploymentComponentSpecs(
                            spec=spec
                            # TODO [HIGH]: Add support for other component types (e.g. graph)
                        )
                    ],
                )
            ]
        else:
            predictors = [
                SeldonDeploymentPredictor(
                    name=model_name or "",
                    graph=SeldonDeploymentPredictiveUnit(
                        name="classifier",
                        type=SeldonDeploymentPredictiveUnitType.MODEL,
                        modelUri=model_uri or "",
                        implementation=implementation or "",
                        envSecretRefName=secret_name,
                        parameters=parameters,
                        serviceAccountName=serviceAccountName,
                    ),
                    engineResources=engineResources,
                )
            ]

        return SeldonDeployment(
            metadata=SeldonDeploymentMetadata(
                name=name, labels=labels, annotations=annotations
            ),
            spec=SeldonDeploymentSpec(name=name, predictors=predictors),
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

    def get_error(self) -> str | None:
        """Get a message describing the error, if in an error state.

        Returns:
            A message describing the error, if in an error state, otherwise
            None.
        """
        if self.status and self.is_failed():
            return self.status.description
        return None

    def get_pending_message(self) -> str | None:
        """Get a message describing the pending conditions of the Seldon Deployment.

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

    model_config = ConfigDict(
        # validate attribute assignments
        validate_assignment=True,
        # Ignore extra attributes from the CRD that are not reflected here
        extra="ignore",
    )


class SeldonClientError(Exception):
    """Base exception class for all exceptions raised by the SeldonClient."""


class SeldonClientTimeout(SeldonClientError):
    """Raised when the Seldon client timed out while waiting for a resource to reach the expected status."""


class SeldonDeploymentExistsError(SeldonClientError):
    """Raised when a SeldonDeployment resource cannot be created because a resource with the same name already exists."""


class SeldonDeploymentNotFoundError(SeldonClientError):
    """Raised when a particular SeldonDeployment resource is not found or is not managed by ZenML."""


class SeldonClient:
    """A client for interacting with Seldon Deployments."""

    def __init__(
        self,
        context: str | None,
        namespace: str | None,
        kube_client: k8s_client.ApiClient | None = None,
    ):
        """Initialize a Seldon Core client.

        Args:
            context: the Kubernetes context to use.
            namespace: the Kubernetes namespace to use.
            kube_client: a Kubernetes client to use.
        """
        self._namespace = namespace
        self._initialize_k8s_clients(context=context, kube_client=kube_client)

    def _initialize_k8s_clients(
        self,
        context: str | None,
        kube_client: k8s_client.ApiClient | None = None,
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
                raise SeldonClientError(
                    "The Kubernetes namespace must be explicitly "
                    "configured when running outside of a cluster."
                )
            try:
                k8s_config.load_kube_config(
                    context=context, persist_config=False
                )
            except k8s_config.config_exception.ConfigException as e:
                raise SeldonClientError(
                    "Could not load the Kubernetes configuration"
                ) from e
        self._core_api = k8s_client.CoreV1Api()
        self._custom_objects_api = k8s_client.CustomObjectsApi()

    @staticmethod
    def sanitize_labels(labels: dict[str, str]) -> None:
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
            SeldonClientError: if an unknown error occurs during the creation of
                the deployment.
        """
        try:
            logger.debug(f"Creating SeldonDeployment resource: {deployment}")

            # mark the deployment as managed by ZenML, to differentiate
            # between deployments that are created by ZenML and those that
            # are not
            deployment.mark_as_managed_by_zenml()

            body_deploy = deployment.model_dump(exclude_none=True)
            response = (
                self._custom_objects_api.create_namespaced_custom_object(
                    group="machinelearning.seldon.io",
                    version="v1",
                    namespace=self._namespace,
                    plural="seldondeployments",
                    body=body_deploy,
                    _request_timeout=poll_timeout or None,
                )
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
            SeldonClientError: if an unknown error occurs during the deployment
                removal.
        """
        try:
            logger.debug(f"Deleting SeldonDeployment resource: {name}")

            # call `get_deployment` to check that the deployment exists
            # and is managed by ZenML. It will raise
            # a SeldonDeploymentNotFoundError otherwise
            self.get_deployment(name=name)

            response = (
                self._custom_objects_api.delete_namespaced_custom_object(
                    group="machinelearning.seldon.io",
                    version="v1",
                    namespace=self._namespace,
                    plural="seldondeployments",
                    name=name,
                    _request_timeout=poll_timeout or None,
                    grace_period_seconds=0 if force else None,
                )
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
                body=deployment.model_dump(exclude_none=True),
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
        name: str | None = None,
        labels: dict[str, str] | None = None,
        fields: dict[str, str] | None = None,
    ) -> list[SeldonDeployment]:
        """Find all ZenML-managed Seldon Core deployment resources matching the given criteria.

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
        tail: int | None = None,
    ) -> Generator[str, bool, None]:
        """Get the logs of a Seldon Core deployment resource.

        Args:
            name: the name of the Seldon Core deployment to get logs for.
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
        secret_values: dict[str, Any],
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


def create_seldon_core_custom_spec(
    model_uri: str | None,
    custom_docker_image: str | None,
    secret_name: str | None,
    command: list[str] | None,
    container_registry_secret_name: str | None = None,
) -> k8s_client.V1PodSpec:
    """Create a custom pod spec for the seldon core container.

    Args:
        model_uri: The URI of the model to load.
        custom_docker_image: The docker image to use.
        secret_name: The name of the Kubernetes secret to use.
        command: The command to run in the container.
        container_registry_secret_name: The name of the secret to use for docker
            image pull.

    Returns:
        A pod spec for the seldon core container.
    """
    volume = k8s_client.V1Volume(
        name="classifier-provision-location",
        empty_dir={},
    )
    init_container = k8s_client.V1Container(
        name="classifier-model-initializer",
        image="seldonio/rclone-storage-initializer:1.14.0-dev",
        image_pull_policy="IfNotPresent",
        args=[model_uri, "/mnt/models"],
        volume_mounts=[
            k8s_client.V1VolumeMount(
                name="classifier-provision-location", mount_path="/mnt/models"
            )
        ],
    )
    if secret_name:
        init_container.env_from = [
            k8s_client.V1EnvFromSource(
                secret_ref=k8s_client.V1SecretEnvSource(
                    name=secret_name, optional=False
                )
            )
        ]
    container = k8s_client.V1Container(
        name="classifier",
        image=custom_docker_image,
        image_pull_policy="IfNotPresent",
        command=command,
        volume_mounts=[
            k8s_client.V1VolumeMount(
                name="classifier-provision-location",
                mount_path="/mnt/models",
                read_only=True,
            )
        ],
        ports=[
            k8s_client.V1ContainerPort(container_port=5000),
            k8s_client.V1ContainerPort(container_port=9000),
        ],
    )

    if container_registry_secret_name:
        image_pull_secret = k8s_client.V1LocalObjectReference(
            name=container_registry_secret_name
        )
        spec = k8s_client.V1PodSpec(
            volumes=[
                volume,
            ],
            init_containers=[
                init_container,
            ],
            image_pull_secrets=[image_pull_secret],
            containers=[container],
        )
    else:
        spec = k8s_client.V1PodSpec(
            volumes=[
                volume,
            ],
            init_containers=[
                init_container,
            ],
            containers=[container],
        )

    return api.sanitize_for_serialization(spec)
