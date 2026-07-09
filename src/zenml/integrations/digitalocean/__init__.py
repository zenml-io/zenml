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
"""Initialization of the DigitalOcean integration.

The DigitalOcean integration provides ZenML stack component flavors for
DigitalOcean services: Spaces (S3-compatible object storage) as an artifact
store, and the DigitalOcean Container Registry (DOCR) as a container registry.

Orchestration, sandboxes, and step execution on DigitalOcean run on DigitalOcean
Kubernetes (DOKS) through the existing ``kubernetes`` flavors, so this
integration deliberately does not ship its own orchestrator/sandbox/step-operator
flavors.
"""

from typing import List, Type

from zenml.integrations.constants import DIGITALOCEAN
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

DIGITALOCEAN_SPACES_ARTIFACT_STORE_FLAVOR = "digitalocean_spaces"
DIGITALOCEAN_CONTAINER_REGISTRY_FLAVOR = "digitalocean"


class DigitalOceanIntegration(Integration):
    """Definition of the DigitalOcean integration for ZenML."""

    NAME = DIGITALOCEAN
    # DigitalOcean Spaces is S3-compatible, so the Spaces artifact store reuses
    # the same object-storage dependencies as the S3 artifact store.
    REQUIREMENTS = [
        # Explicitly exclude 2025.3.1 to avoid pulling in the yanked fsspec
        # package with the same version (kept in sync with the S3 integration).
        "s3fs>2022.3.0,!=2025.3.1",
        "boto3",
    ]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the DigitalOcean integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.digitalocean.flavors import (
            DigitalOceanContainerRegistryFlavor,
            DigitalOceanSpacesArtifactStoreFlavor,
        )

        return [
            DigitalOceanSpacesArtifactStoreFlavor,
            DigitalOceanContainerRegistryFlavor,
        ]
