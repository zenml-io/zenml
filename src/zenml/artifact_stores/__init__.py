#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""ZenML's artifact-store stores artifacts in a file system.

In ZenML, the inputs and outputs which go through any step is treated as an
artifact and as its name suggests, an `ArtifactStore` is a place where these
artifacts get stored.

Out of the box, ZenML comes with the `BaseArtifactStore` and
`LocalArtifactStore` implementations. While the `BaseArtifactStore` establishes
an interface for people who want to extend it to their needs, the
`LocalArtifactStore` is a simple implementation for a local setup.

Moreover, additional artifact stores can be found in specific `integrations`
modules, such as the `GCPArtifactStore` in the `gcp` integration and the
`AzureArtifactStore` in the `azure` integration.
"""

from zenml.artifact_stores.base_artifact_store import (
    BaseArtifactStore,
    BaseArtifactStoreConfig,
    BaseArtifactStoreFlavor,
)
from zenml.artifact_stores.local_artifact_store import (
    LocalArtifactStore,
    LocalArtifactStoreConfig,
    LocalArtifactStoreFlavor,
)

__all__ = [
    "BaseArtifactStore",
    "BaseArtifactStoreConfig",
    "BaseArtifactStoreFlavor",
    "LocalArtifactStore",
    "LocalArtifactStoreConfig",
    "LocalArtifactStoreFlavor",
]
