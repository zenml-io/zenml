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
"""Google Cloud Run sandbox flavor."""

from typing import TYPE_CHECKING, Optional, Type
from urllib.parse import urlparse

from pydantic import Field, field_validator

from zenml.integrations.gcp import (
    GCP_CLOUDRUN_SANDBOX_FLAVOR,
    GCP_CONNECTOR_TYPE,
    GCP_RESOURCE_TYPE,
)
from zenml.integrations.gcp.flavors.gcp_artifact_store_flavor import (
    GCP_PATH_PREFIX,
)
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsConfigMixin,
)
from zenml.models import ServiceConnectorRequirements
from zenml.sandboxes import (
    BaseSandboxConfig,
    BaseSandboxFlavor,
    BaseSandboxSettings,
)

if TYPE_CHECKING:
    from zenml.integrations.gcp.sandboxes import CloudRunSandbox


DEFAULT_BRIDGE_TIMEOUT_MS = 120_000


class CloudRunSandboxSettings(BaseSandboxSettings):
    """Per-step settings for the Cloud Run sandbox."""

    timeout_ms: int = Field(
        default=DEFAULT_BRIDGE_TIMEOUT_MS,
        ge=1,
        description="Per-exec timeout in milliseconds, passed to the bridge "
        "as timeout_ms on POST /v1/sandbox/:id/exec. Must stay below the "
        "Cloud Run service request timeout of the bridge (max 60 minutes). "
        "Example: 60000 for a one-minute cap",
    )
    cwd: Optional[str] = Field(
        default=None,
        description="Default working directory for commands executed inside "
        "the sandbox. Must be an absolute path in the sandbox filesystem. "
        "Example: '/tmp/workspace'",
    )
    allow_egress: bool = Field(
        default=False,
        description="Controls outbound network access for sandboxes created "
        "with these settings. Cloud Run sandboxes have no egress by default; "
        "setting this to True passes --allow-egress at sandbox creation. "
        "Keep disabled when running untrusted code that has no reason to "
        "reach the network",
    )


class CloudRunSandboxConfig(
    BaseSandboxConfig, GoogleCredentialsConfigMixin, CloudRunSandboxSettings
):
    """Configuration for the Cloud Run sandbox component."""

    service_url: str = Field(
        description="URL of the Cloud Run service deployed with "
        "--sandbox-launcher that runs the ZenML sandbox bridge. Must be an "
        "https:// URL. Example: "
        "'https://zenml-sandbox-bridge-abc123-ew.a.run.app'",
    )
    audience: Optional[str] = Field(
        default=None,
        description="Audience claim for the Google-signed ID tokens sent to "
        "the bridge. Defaults to service_url, which is what Cloud Run IAM "
        "expects; only set this when the bridge sits behind a load balancer "
        "with a custom audience. Example: 'https://bridge.example.com'",
    )
    allow_unauthenticated: bool = Field(
        default=False,
        description="Skips ID-token authentication entirely. Only for "
        "bridges deployed with --allow-unauthenticated, which exposes the "
        "sandbox launcher to the public internet and is strongly "
        "discouraged outside local experiments",
    )
    snapshot_uri_prefix: Optional[str] = Field(
        default=None,
        description="Cloud Storage URI prefix under which sandbox snapshots "
        "are stored, enabling create_snapshot()/restore(). The bridge "
        "service account needs read/write access to this location. "
        "Example: 'gs://my-bucket/zenml-sandbox-snapshots'",
    )

    @field_validator("service_url")
    @classmethod
    def _validate_service_url_scheme(cls, value: str) -> str:
        """Require https for the bridge URL.

        Args:
            value: The configured service URL.

        Returns:
            The validated URL, unchanged.

        Raises:
            ValueError: If the URL scheme is not https (or http to
                localhost/127.0.0.1).
        """
        parsed = urlparse(value)
        if parsed.scheme == "https":
            return value
        if parsed.scheme == "http" and parsed.hostname in (
            "localhost",
            "127.0.0.1",
        ):
            return value
        raise ValueError(
            f"Invalid service_url '{value}': the Cloud Run sandbox bridge "
            "must be reached over https (an identity token is sent as a "
            "bearer token on every request). Plain http is only allowed "
            "for localhost/127.0.0.1 when testing a local bridge."
        )

    @field_validator("snapshot_uri_prefix")
    @classmethod
    def _validate_snapshot_uri_prefix(
        cls, value: Optional[str]
    ) -> Optional[str]:
        """Require a gs:// URI for the snapshot location.

        Args:
            value: The configured snapshot URI prefix.

        Returns:
            The validated URI prefix with any trailing slash removed.

        Raises:
            ValueError: If the URI does not use the gs:// scheme.
        """
        if value is None:
            return None
        if not value.startswith(GCP_PATH_PREFIX):
            raise ValueError(
                f"Invalid snapshot_uri_prefix '{value}': must be a Cloud "
                f"Storage URI starting with '{GCP_PATH_PREFIX}'."
            )
        return value.rstrip("/")

    @property
    def is_remote(self) -> bool:
        """Cloud Run sandboxes run on Google's infrastructure.

        Returns:
            ``True``: the ZenML client is not the host.
        """
        return True


class CloudRunSandboxFlavor(BaseSandboxFlavor):
    """Google Cloud Run sandbox flavor."""

    @property
    def name(self) -> str:
        """Flavor name.

        Returns:
            ``"cloudrun"``.
        """
        return GCP_CLOUDRUN_SANDBOX_FLAVOR

    @property
    def display_name(self) -> str:
        """Human-readable flavor name.

        Returns:
            The display name.
        """
        return "Cloud Run"

    @property
    def service_connector_requirements(
        self,
    ) -> Optional[ServiceConnectorRequirements]:
        """Service connector requirements for this flavor.

        Returns:
            Requirements matching the GCP service connector's generic
            resource type.
        """
        return ServiceConnectorRequirements(
            connector_type=GCP_CONNECTOR_TYPE,
            resource_type=GCP_RESOURCE_TYPE,
        )

    @property
    def docs_url(self) -> Optional[str]:
        """URL to user-facing docs for this flavor.

        Returns:
            The flavor docs URL.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """URL to SDK docs for this flavor.

        Returns:
            The flavor SDK docs URL.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """Dashboard logo URL.

        Returns:
            The flavor logo URL.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/sandbox/cloudrun.png"

    @property
    def config_class(self) -> Type[CloudRunSandboxConfig]:
        """Config class.

        Returns:
            ``CloudRunSandboxConfig``.
        """
        return CloudRunSandboxConfig

    @property
    def implementation_class(self) -> Type["CloudRunSandbox"]:
        """Implementation class.

        Returns:
            ``CloudRunSandbox``.
        """
        from zenml.integrations.gcp.sandboxes import CloudRunSandbox

        return CloudRunSandbox
