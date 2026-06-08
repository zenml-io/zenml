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
"""Cloudflare integration flavors."""

from zenml.integrations.cloudflare.flavors.cloudflare_container_registry_flavor import (
    CloudflareContainerRegistryFlavor,
)
from zenml.integrations.cloudflare.flavors.cloudflare_r2_artifact_store_flavor import (
    R2ArtifactStoreConfig,
    R2ArtifactStoreFlavor,
)
from zenml.integrations.cloudflare.flavors.cloudflare_sandbox_flavor import (
    CloudflareSandboxConfig,
    CloudflareSandboxFlavor,
    CloudflareSandboxSettings,
)

__all__ = [
    "R2ArtifactStoreFlavor",
    "R2ArtifactStoreConfig",
    "CloudflareContainerRegistryFlavor",
    "CloudflareSandboxConfig",
    "CloudflareSandboxFlavor",
    "CloudflareSandboxSettings",
]
