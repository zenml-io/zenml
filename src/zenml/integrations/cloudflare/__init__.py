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
"""Initialization of the Cloudflare integration.

The Cloudflare integration provides stack components backed by Cloudflare's
developer platform: an artifact store on top of R2 (S3-compatible object
storage) and a container registry on top of the Cloudflare managed registry.
"""
from typing import List, Type

from zenml.integrations.constants import CLOUDFLARE
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

CLOUDFLARE_R2_ARTIFACT_STORE_FLAVOR = "r2"
CLOUDFLARE_CONTAINER_REGISTRY_FLAVOR = "cloudflare"


class CloudflareIntegration(Integration):
    """Definition of the Cloudflare integration for ZenML."""

    NAME = CLOUDFLARE
    # R2 is S3-compatible, so the artifact store reuses the S3 filesystem
    # stack. boto3 is required for the underlying client.
    REQUIREMENTS = [
        # Explicitly exclude 2025.3.1 to avoid pulling in the yanked fsspec
        # package with the same version
        "s3fs>2022.3.0,!=2025.3.1",
        "boto3",
    ]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the Cloudflare integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.cloudflare.flavors import (
            CloudflareContainerRegistryFlavor,
            R2ArtifactStoreFlavor,
        )

        return [
            R2ArtifactStoreFlavor,
            CloudflareContainerRegistryFlavor,
        ]
