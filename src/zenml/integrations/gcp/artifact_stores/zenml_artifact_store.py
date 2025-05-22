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
"""Implementation of the ZenML Artifact Store."""

from zenml.integrations.gcp.artifact_stores.gcp_artifact_store import (  # noqa
    GCPArtifactStore,
)


class ZenMLArtifactStore(GCPArtifactStore):
    """ZenML specialized Artifact Store that inherits from GCP Artifact Store.

    This class extends the GCPArtifactStore to provide ZenML-specific
    functionality and customizations for artifact storage.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the ZenML Artifact Store.

        Args:
            *args: Arguments to pass to the parent class.
            **kwargs: Keyword arguments to pass to the parent class.
        """
        super().__init__(*args, **kwargs)
