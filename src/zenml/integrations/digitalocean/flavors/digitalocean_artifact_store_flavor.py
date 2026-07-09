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
"""DigitalOcean Spaces artifact store flavor.

DigitalOcean Spaces is S3-compatible, so this flavor subclasses the S3
implementation rather than duplicating it. The config layer only validates
user-provided values (the Spaces ``region``); the region-derived endpoint URL
is applied in the artifact store implementation so it is not persisted as stack
component configuration.
"""

from typing import TYPE_CHECKING, Optional, Type

from pydantic import Field, field_validator, model_validator

from zenml.integrations.digitalocean import (
    DIGITALOCEAN_SPACES_ARTIFACT_STORE_FLAVOR,
)
from zenml.integrations.s3.flavors.s3_artifact_store_flavor import (
    S3ArtifactStoreConfig,
    S3ArtifactStoreFlavor,
)
from zenml.models import ServiceConnectorRequirements

if TYPE_CHECKING:
    from zenml.integrations.digitalocean.artifact_stores import (
        DigitalOceanSpacesArtifactStore,
    )

# DigitalOcean Spaces regions. The endpoint URL is
# ``https://<region>.digitaloceanspaces.com``.
DIGITALOCEAN_SPACES_REGIONS = [
    "nyc3",
    "ams3",
    "sfo2",
    "sfo3",
    "sgp1",
    "fra1",
    "syd1",
    "blr1",
]


def spaces_endpoint_url(region: str) -> str:
    """Build the DigitalOcean Spaces endpoint URL for a region.

    Args:
        region: The DigitalOcean Spaces region, e.g. 'fra1'.

    Returns:
        The Spaces endpoint URL for that region.
    """
    return f"https://{region}.digitaloceanspaces.com"


class DigitalOceanSpacesArtifactStoreConfig(S3ArtifactStoreConfig):
    """Configuration for the DigitalOcean Spaces artifact store.

    Inherits every option of the S3 artifact store (Spaces is S3-compatible)
    and adds a ``region`` field. The bucket URI continues to use the ``s3://``
    scheme because the underlying filesystem (s3fs) addresses Spaces buckets
    through the S3 API.

    Example:
        ```
        zenml artifact-store register do_spaces \
          --flavor=digitalocean_spaces --path=s3://my-space --region=fra1
        ```
    """

    region: Optional[str] = Field(
        default=None,
        description="DigitalOcean Spaces region, used to build the Spaces "
        "endpoint URL. Must be one of DigitalOcean's Spaces regions, for "
        "example 'nyc3', 'ams3', 'fra1', 'sgp1'. Not required if "
        "client_kwargs['endpoint_url'] is provided explicitly.",
    )

    @field_validator("region")
    @classmethod
    def _validate_region(cls, region: Optional[str]) -> Optional[str]:
        """Validates that ``region`` is a known Spaces region.

        Args:
            region: The region to validate.

        Returns:
            The validated region.

        Raises:
            ValueError: If the region is not a known Spaces region.
        """
        if region is not None and region not in DIGITALOCEAN_SPACES_REGIONS:
            raise ValueError(
                f"Unknown DigitalOcean Spaces region '{region}'. Known "
                f"regions: {', '.join(DIGITALOCEAN_SPACES_REGIONS)}."
            )
        return region

    @model_validator(mode="after")
    def _require_region_or_endpoint(
        self,
    ) -> "DigitalOceanSpacesArtifactStoreConfig":
        """Requires either a ``region`` or an explicit endpoint URL.

        Returns:
            The validated config.

        Raises:
            ValueError: If neither ``region`` nor an explicit endpoint URL is
                set, since the Spaces endpoint cannot be determined otherwise.
        """
        has_endpoint = bool(
            self.client_kwargs and self.client_kwargs.get("endpoint_url")
        )
        if not self.region and not has_endpoint:
            raise ValueError(
                "The DigitalOcean Spaces artifact store needs either a "
                "`region` (for example 'fra1') or an explicit "
                "client_kwargs['endpoint_url'] to locate the Spaces endpoint."
            )
        return self


class DigitalOceanSpacesArtifactStoreFlavor(S3ArtifactStoreFlavor):
    """Flavor of the DigitalOcean Spaces artifact store."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return DIGITALOCEAN_SPACES_ARTIFACT_STORE_FLAVOR

    @property
    def display_name(self) -> str:
        """Display name of the flavor.

        Returns:
            The display name of the flavor.
        """
        return "DigitalOcean Spaces"

    @property
    def service_connector_requirements(
        self,
    ) -> Optional[ServiceConnectorRequirements]:
        """Service connector resource requirements for service connectors.

        A dedicated DigitalOcean service connector is a planned follow-up; until
        it exists, the Spaces artifact store authenticates with the ``key`` /
        ``secret`` Spaces access keys directly, so no connector is advertised.

        Returns:
            None, until a DigitalOcean service connector is available.
        """
        return None

    @property
    def logo_url(self) -> str:
        """A URL to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/artifact_store/digitalocean.png"

    @property
    def config_class(self) -> Type[DigitalOceanSpacesArtifactStoreConfig]:
        """The config class of the flavor.

        Returns:
            The config class of the flavor.
        """
        return DigitalOceanSpacesArtifactStoreConfig

    @property
    def implementation_class(self) -> Type["DigitalOceanSpacesArtifactStore"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class for this flavor.
        """
        from zenml.integrations.digitalocean.artifact_stores import (
            DigitalOceanSpacesArtifactStore,
        )

        return DigitalOceanSpacesArtifactStore
