#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
The Azure integration submodule provides a way to run ZenML pipelines in a cloud
environment. Specifically, it allows the use of cloud artifact stores,
and an `io` module to handle file operations on Azure Blob Storage.
"""
from typing import List

from zenml.enums import StackComponentType
from zenml.integrations.constants import AZURE
from zenml.integrations.integration import Integration
from zenml.zen_stores.models import FlavorWrapper

AZURE_ARTIFACT_STORE_FLAVOR = "azure"


class AzureIntegration(Integration):
    """Definition of Azure integration for ZenML."""

    NAME = AZURE
    REQUIREMENTS = ["adlfs==2021.10.0"]

    @classmethod
    def flavors(cls) -> List[FlavorWrapper]:
        """Declares the flavors for the integration."""
        return [
            FlavorWrapper(
                name=AZURE_ARTIFACT_STORE_FLAVOR,
                source="zenml.integrations.azure.artifact_stores.AzureArtifactStore",
                type=StackComponentType.ARTIFACT_STORE,
                integration=cls.NAME,
            )
        ]


AzureIntegration.check_installation()
