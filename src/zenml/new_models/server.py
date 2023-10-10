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

    version: str = Field(
        title="The ZenML version that the server is running.",
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

    def is_local(self) -> bool:
        """Return whether the server is running locally.

        Returns:
            True if the server is running locally, False otherwise.
        """
        from zenml.config.global_config import GlobalConfiguration

        # Local ZenML servers are identifiable by the fact that their
        # server ID is the same as the local client (user) ID.
        return self.id == GlobalConfiguration().user_id
