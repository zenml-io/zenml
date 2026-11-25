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

import re
from typing import TYPE_CHECKING, Optional, Type

from pydantic import Field, model_validator

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

# Spaces region slugs are short lowercase datacenter codes ending in a digit
# (nyc3, ams3, fra1, lon1, ...). Validating the format instead of a hardcoded
# allowlist keeps the flavor usable when DigitalOcean adds regions, while
# still rejecting values that would corrupt the derived endpoint URL.
DIGITALOCEAN_SPACES_REGION_PATTERN = re.compile(r"^[a-z]{2,6}[0-9]{1,2}$")


class DigitalOceanSpacesArtifactStoreConfig(S3ArtifactStoreConfig):
    """Configuration for the DigitalOcean Spaces artifact store.

    Inherits every option of the S3 artifact store (Spaces is S3-compatible)
    and adds a ``region`` field. The bucket URI continues to use the ``s3://``
    scheme because the underlying filesystem (s3fs) addresses Spaces buckets
    through the S3 API.

    Example:
        ```
        zenml artifact-store register do_spaces \
          --flavor=digitalocean --path=s3://my-space --region=fra1
        ```
    """

    region: Optional[str] = Field(
        default=None,
        description="DigitalOcean Spaces region slug, used to build the "
        "Spaces endpoint URL. Must be a lowercase datacenter code such as "
        "'nyc3', 'ams3', 'fra1' or 'lon1'. Not required if "
        "client_kwargs['endpoint_url'] is provided explicitly.",
    )

    @model_validator(mode="after")
    def _validate_region_or_endpoint(
        self,
    ) -> "DigitalOceanSpacesArtifactStoreConfig":
        """Validates the region slug, requiring one unless an endpoint is set.

        The region format is validated instead of a hardcoded region allowlist
        so that regions DigitalOcean adds in the future work without a ZenML
        release.

        Returns:
            The validated config.

        Raises:
            ValueError: If the region is not a valid Spaces region slug, or if
                neither ``region`` nor an explicit endpoint URL is set (the
                Spaces endpoint cannot be determined otherwise).
        """
        if self.region:
            if not DIGITALOCEAN_SPACES_REGION_PATTERN.match(self.region):
                raise ValueError(
                    f"Invalid DigitalOcean Spaces region '{self.region}'. "
                    f"Expected a lowercase datacenter slug such as 'nyc3', "
                    f"'ams3', 'fra1' or 'lon1'."
                )
        elif not (
            self.client_kwargs and self.client_kwargs.get("endpoint_url")
        ):
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
