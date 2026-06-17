#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Backblaze B2 artifact store flavor.

B2 is S3-compatible, so this flavor subclasses the S3 implementation
rather than duplicating it. The config layer only validates user-provided
values. Runtime fallbacks such as environment credentials and endpoint/user
agent defaults are applied in the artifact store implementation so they are
not persisted as stack component configuration.
"""

import json
from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
    Type,
)

from pydantic import field_validator

from zenml.integrations.b2 import B2_ARTIFACT_STORE_FLAVOR
from zenml.integrations.s3.flavors.s3_artifact_store_flavor import (
    S3ArtifactStoreConfig,
    S3ArtifactStoreFlavor,
)
from zenml.models import ServiceConnectorRequirements

if TYPE_CHECKING:
    from zenml.integrations.b2.artifact_stores import B2ArtifactStore

# Default Backblaze B2 S3 API endpoint. The region segment of the
# hostname (us-west-004) determines which B2 region is used; users can
# override `client_kwargs.endpoint_url` to target a different region
# (e.g. us-west-001/002, eu-central-003).
DEFAULT_B2_ENDPOINT_URL = "https://s3.us-west-004.backblazeb2.com"

# Backblaze publishes application keys under these env vars. We map them
# to the AWS-style key/secret slots that the underlying S3 client uses.
B2_KEY_ID_ENV_VAR = "B2_APPLICATION_KEY_ID"
B2_APPLICATION_KEY_ENV_VAR = "B2_APPLICATION_KEY"

B2_USER_AGENT = "b2ai-zenml"


class B2ArtifactStoreConfig(S3ArtifactStoreConfig):
    """Configuration for the Backblaze B2 Artifact Store.

    Inherits all fields from :class:`S3ArtifactStoreConfig`. The bucket
    URI continues to use the ``s3://`` scheme because the underlying
    filesystem (s3fs) addresses B2 buckets through the S3 API.
    """

    @field_validator("client_kwargs", "config_kwargs", mode="before")
    @classmethod
    def _parse_json_dict(cls, value: Any) -> Any:
        """Parse JSON string dictionaries passed through the CLI.

        Args:
            value: The raw field value.

        Raises:
            ValueError: If the value is a JSON string that does not decode to
                a dictionary.

        Returns:
            The parsed dictionary for JSON strings, otherwise the original
            value so Pydantic can perform normal validation.
        """
        if not isinstance(value, str):
            return value

        parsed_value = json.loads(value)
        if not isinstance(parsed_value, dict):
            raise ValueError("Expected a JSON object.")
        return parsed_value


class B2ArtifactStoreFlavor(S3ArtifactStoreFlavor):
    """Flavor of the Backblaze B2 artifact store."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return B2_ARTIFACT_STORE_FLAVOR

    @property
    def display_name(self) -> str:
        """Display name of the flavor.

        Returns:
            The display name of the flavor.
        """
        return "Backblaze B2"

    @property
    def service_connector_requirements(
        self,
    ) -> Optional[ServiceConnectorRequirements]:
        """Service connector resource requirements for B2.

        A dedicated B2 service connector is not yet shipped; until one
        lands, no connector requirements are advertised so users wire
        credentials directly into the flavor config.

        Returns:
            ``None``: no service connector is currently required.
        """
        return None

    @property
    def logo_url(self) -> str:
        """Logo URL for the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/artifact_store/b2.png"

    @property
    def config_class(self) -> Type[B2ArtifactStoreConfig]:
        """The config class of the flavor.

        Returns:
            The config class of the flavor.
        """
        return B2ArtifactStoreConfig

    @property
    def implementation_class(self) -> Type["B2ArtifactStore"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class for this flavor.
        """
        from zenml.integrations.b2.artifact_stores import B2ArtifactStore

        return B2ArtifactStore
