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
"""Initialization of the Backblaze B2 integration.

The B2 integration registers a dedicated `b2` artifact store flavor that
reuses the S3-compatible implementation, defaulting the endpoint URL to
Backblaze B2's S3 API. It depends on the same runtime libraries as the
S3 integration (`s3fs`, `boto3`) and is intentionally a thin subclass:
all filesystem behavior is inherited from the S3 artifact store.
"""

from typing import List, Type

from zenml.integrations.constants import B2
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

B2_ARTIFACT_STORE_FLAVOR = "b2"


class B2Integration(Integration):
    """Definition of the Backblaze B2 integration for ZenML."""

    NAME = B2
    # The B2 artifact store reuses the S3-compatible filesystem and
    # boto3 client used by the S3 integration; mirror its requirements
    # so installing `zenml[b2]` is self-sufficient.
    REQUIREMENTS = [
        "s3fs>2022.3.0,!=2025.3.1",
        "boto3",
    ]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the B2 integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.b2.flavors import B2ArtifactStoreFlavor

        return [B2ArtifactStoreFlavor]
