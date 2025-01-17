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
"""Model definitions for ZenML servers."""

from datetime import datetime
from typing import Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from zenml.enums import AuthScheme, SecretsStoreType
from zenml.utils.enum_utils import StrEnum


class ServerDeploymentType(StrEnum):
    """Enum for server deployment types."""

    LOCAL = "local"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    ALPHA = "alpha"
    OTHER = "other"
    HF_SPACES = "hf_spaces"
    SANDBOX = "sandbox"
    CLOUD = "cloud"


class ServerDatabaseType(StrEnum):
    """Enum for server database types."""

    SQLITE = "sqlite"
    MYSQL = "mysql"
    OTHER = "other"


class ServerModel(BaseModel):
    """Domain model for ZenML servers."""

    id: UUID = Field(default_factory=uuid4, title="The unique server id.")

    name: Optional[str] = Field(None, title="The name of the ZenML server.")

    version: str = Field(
        title="The ZenML version that the server is running.",
    )

    active: bool = Field(
        True, title="Flag to indicate whether the server is active."
    )

    debug: bool = Field(
        False, title="Flag to indicate whether ZenML is running on debug mode."
    )

    deployment_type: ServerDeploymentType = Field(
        ServerDeploymentType.OTHER,
        title="The ZenML server deployment type.",
    )
    database_type: ServerDatabaseType = Field(
        ServerDatabaseType.OTHER,
        title="The database type that the server is using.",
    )
    secrets_store_type: SecretsStoreType = Field(
        SecretsStoreType.NONE,
        title="The type of secrets store that the server is using.",
    )
    auth_scheme: AuthScheme = Field(
        title="The authentication scheme that the server is using.",
    )
    server_url: str = Field(
        "",
        title="The URL where the ZenML server API is reachable. If not "
        "specified, the clients will use the same URL used to connect them to "
        "the ZenML server.",
    )
    dashboard_url: str = Field(
        "",
        title="The URL where the ZenML dashboard is reachable. If "
        "not specified, the `server_url` value will be used instead.",
    )
    analytics_enabled: bool = Field(
        default=True,  # We set a default for migrations from < 0.57.0
        title="Enable server-side analytics.",
    )

    metadata: Dict[str, str] = Field(
        {},
        title="The metadata associated with the server.",
    )

    last_user_activity: Optional[datetime] = Field(
        None,
        title="Timestamp of latest user activity traced on the server.",
    )

    pro_dashboard_url: Optional[str] = Field(
        None,
        title="The base URL of the ZenML Pro dashboard to which the server "
        "is connected. Only set if the server is a ZenML Pro server.",
    )

    pro_api_url: Optional[str] = Field(
        None,
        title="The base URL of the ZenML Pro API to which the server is "
        "connected. Only set if the server is a ZenML Pro server.",
    )

    pro_organization_id: Optional[UUID] = Field(
        None,
        title="The ID of the ZenML Pro organization to which the server is "
        "connected. Only set if the server is a ZenML Pro server.",
    )

    pro_organization_name: Optional[str] = Field(
        None,
        title="The name of the ZenML Pro organization to which the server is "
        "connected. Only set if the server is a ZenML Pro server.",
    )

    pro_tenant_id: Optional[UUID] = Field(
        None,
        title="The ID of the ZenML Pro tenant to which the server is connected. "
        "Only set if the server is a ZenML Pro server.",
    )

    pro_tenant_name: Optional[str] = Field(
        None,
        title="The name of the ZenML Pro tenant to which the server is connected. "
        "Only set if the server is a ZenML Pro server.",
    )

    def is_local(self) -> bool:
        """Return whether the server is running locally.

        Returns:
            True if the server is running locally, False otherwise.
        """
        from zenml.config.global_config import GlobalConfiguration

        # Local ZenML servers are identifiable by the fact that their
        # server ID is the same as the local client (user) ID.
        return self.id == GlobalConfiguration().user_id

    def is_pro_server(self) -> bool:
        """Return whether the server is a ZenML Pro server.

        Returns:
            True if the server is a ZenML Pro server, False otherwise.
        """
        return self.deployment_type == ServerDeploymentType.CLOUD


class ServerLoadInfo(BaseModel):
    """Domain model for ZenML server load information."""

    threads: int = Field(
        title="Number of threads that the server is currently using."
    )

    db_connections_total: int = Field(
        title="Total number of database connections (active and idle) that the "
        "server currently has established."
    )

    db_connections_active: int = Field(
        title="Number of database connections that the server is currently "
        "actively using to make queries or transactions."
    )

    db_connections_overflow: int = Field(
        title="Number of overflow database connections that the server is "
        "currently actively using to make queries or transactions."
    )
