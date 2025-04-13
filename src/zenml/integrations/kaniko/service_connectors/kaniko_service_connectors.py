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

class KanikoCredeintials(AuthenticationConfig):
    """
    Kaniko credentials for Docker registry authentication.
    """

    # The Docker registry URL
    registry_url: str = Field(
        description="The URL of the Docker registry.",
        title="Docker Registry URL",
    )

    # The username for Docker registry authentication
    username: str = Field(
        description="The username for Docker registry authentication.",
        title="Username",
    )

    # The password for Docker registry authentication
    password: str = Field(
        description="The password for Docker registry authentication.",
        title="Password",
    )