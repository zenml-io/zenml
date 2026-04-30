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
rather than duplicating it. The only differences are:

- A B2-specific default ``endpoint_url`` (Backblaze's US-West-004 region)
  is injected into ``client_kwargs`` if the user does not provide one.
- ``B2_APPLICATION_KEY_ID`` / ``B2_APPLICATION_KEY`` environment variables
  are honored as a fallback for ``key`` / ``secret``, in addition to the
  AWS-style credential resolution inherited from the S3 flavor.
- A ``b2ai-zenml`` suffix is appended to ``config_kwargs.user_agent_extra``
  so traffic from this integration is identifiable in B2-side server logs
  (analogous to MLflow's existing B2 attribution convention). The suffix
  is added once and merged with any user-provided ``user_agent_extra``.
"""

import os
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Optional,
    Type,
)

from pydantic import model_validator

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

_B2_USER_AGENT = "b2ai-zenml"


class B2ArtifactStoreConfig(S3ArtifactStoreConfig):
    """Configuration for the Backblaze B2 Artifact Store.

    Inherits all fields from :class:`S3ArtifactStoreConfig`. The bucket
    URI continues to use the ``s3://`` scheme because the underlying
    filesystem (s3fs) addresses B2 buckets through the S3 API.
    """

    @model_validator(mode="before")
    @classmethod
    def _apply_b2_defaults(cls, data: Any) -> Any:
        """Apply B2-specific defaults for endpoint URL and credentials.

        Runs before model construction so values can be injected into
        ``client_kwargs`` (which becomes immutable post-validation in
        Pydantic v2). Sets the default Backblaze B2 endpoint URL when the
        user has not configured one, and falls back to the
        ``B2_APPLICATION_KEY_ID`` / ``B2_APPLICATION_KEY`` environment
        variables for credentials when no key/secret is provided on the
        config or via AWS-style env vars.

        Args:
            data: Raw input data dict (or other value) prior to validation.

        Returns:
            The (possibly mutated) raw input data with B2 defaults applied.
        """
        if not isinstance(data, dict):
            return data

        client_kwargs: Dict[str, Any] = dict(data.get("client_kwargs") or {})
        if not client_kwargs.get("endpoint_url"):
            client_kwargs["endpoint_url"] = DEFAULT_B2_ENDPOINT_URL
            data["client_kwargs"] = client_kwargs

        config_kwargs: Dict[str, Any] = dict(data.get("config_kwargs") or {})
        existing_ua = (config_kwargs.get("user_agent_extra") or "").strip()
        if _B2_USER_AGENT not in existing_ua:
            config_kwargs["user_agent_extra"] = (
                f"{existing_ua} {_B2_USER_AGENT}".strip()
            )
            data["config_kwargs"] = config_kwargs

        if not data.get("key"):
            b2_key_id = os.environ.get(B2_KEY_ID_ENV_VAR)
            if b2_key_id:
                data["key"] = b2_key_id
        if not data.get("secret"):
            b2_app_key = os.environ.get(B2_APPLICATION_KEY_ENV_VAR)
            if b2_app_key:
                data["secret"] = b2_app_key

        return data


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
        # TODO: replace with a Backblaze-hosted logo once published to the
        # public flavor logo bucket. Falls back to the S3 logo for now.
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/artifact_store/aws.png"

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
