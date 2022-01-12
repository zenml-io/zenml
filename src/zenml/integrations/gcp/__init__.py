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
"""
The GCP integration submodule provides a way to run ZenML pipelines in a cloud
environment. Specifically, it allows the use of cloud artifact stores, metadata
stores, and an `io` module to handle file operations on Google Cloud Storage (GCS).
"""

from zenml.integrations.constants import GCP
from zenml.integrations.integration import Integration


class GcpIntegration(Integration):
    """Definition of Google Cloud Platform integration for ZenML."""

    NAME = GCP
    REQUIREMENTS = ["gcsfs"]

    @classmethod
    def activate(cls) -> None:
        """Activates the integration."""
        from zenml.integrations.gcp import artifact_stores  # noqa
        from zenml.integrations.gcp import io  # noqa


GcpIntegration.check_installation()
