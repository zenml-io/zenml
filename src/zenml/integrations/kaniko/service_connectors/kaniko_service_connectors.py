import base64
import datetime
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple, cast
from pydantic import Field

from zenml.constants import (
    DOCKER_REGISTRY_RESOURCE_TYPE,
    KUBERNETES_CLUSTER_RESOURCE_TYPE,
)

from zenml.logger import get_logger
from zenml.exceptions import AuthorizationException

from zenml.models import (
    AuthenticationMethodModel,
    ResourceTypeModel,
    ServiceConnectorTypeModel,
)
from zenml.service_connectors.docker_service_connector import (
    DockerAuthenticationMethods,
    DockerConfiguration,
    DockerServiceConnector,
)
from zenml.service_connectors.service_connector import (
    AuthenticationConfig,
    ServiceConnector,
)

class KanikoConnectorConfig(AuthenticationConfig):
    """Kubernetes connection configuration for Kaniko."""

    api_token: str = Field(
        description="Kubernetes API token for authentication.",
        title="API token",
        secret=True,
        default=None
    )

    service_account_name: str = Field(
        description="Kubernetes service account name for authentication.",
        title="Service Account Name",
        default=None,
    )
    kubeconfig: Optional[str] = Field(
        description="Content of the kubecofig file,",
        title="Kubeconfig",
        secret=True,
        default=None,
    )

class KubernetesKanikoServiceConnector(ServiceConnector):
    """Kubernetes Service Connector for Kaniko."""

    config: KanikoConnectorConfig

    @classmethod
    def _get_connector_type(cls):
        return ServiceConnectorTypeModel(
            name="kubernetes-kaniko",
            type="kubernetes",
            description="Kubernetes Service Connector for Kaniko.",
        )