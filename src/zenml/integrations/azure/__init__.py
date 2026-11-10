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
"""Initialization of the ZenML Azure integration.

The Azure integration submodule provides a way to run ZenML pipelines in a cloud
environment. Specifically, it allows the use of cloud artifact stores,
and an `io` module to handle file operations on Azure Blob Storage.
The Azure Step Operator integration submodule provides a way to run ZenML steps
in AzureML.
"""

from typing import List, Type

from zenml.integrations.constants import AZURE
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

AZURE_ARTIFACT_STORE_FLAVOR = "azure"
AZUREML_STEP_OPERATOR_FLAVOR = "azureml"
AZUREML_ORCHESTRATOR_FLAVOR = "azureml"

# Service connector constants
AZURE_CONNECTOR_TYPE = "azure"
AZURE_RESOURCE_TYPE = "azure-generic"
BLOB_RESOURCE_TYPE = "blob-container"


class AzureIntegration(Integration):
    """Definition of Azure integration for ZenML."""

    NAME = AZURE
    REQUIREMENTS = [
        "adlfs>=2021.10.0",
        "azure-identity>=1.4.0",
        "azure-mgmt-containerregistry>=10.0.0",
        "azure-mgmt-containerservice>=20.0.0",
        "azure-mgmt-storage>=20.0.0",
        # The 25.0.0 release splits the azure-mgmt-resource package into
        # multiple packages, some of which don't have a stable (non-prerelease)
        # version yet. See https://github.com/Azure/azure-sdk-for-python/releases/tag/azure-mgmt-resource_25.0.0
        "azure-mgmt-resource>=21.0.0,<25.0.0",
        "azure-storage-blob>=12.17.0,<13.0.0",
        "kubernetes>=18.20.0",
        "requests>=2.27.11,<3.0.0",
        "azure-ai-ml>=1.23.1,<2.0.0",
        # Marshmallow>4.0 leads to the following error with the AzureML SDK:
        # ImportError: cannot import name 'FieldInstanceResolutionError' from 'marshmallow.utils'
        "marshmallow<4.0.0",
    ]
    REQUIREMENTS_IGNORED_ON_UNINSTALL = ["kubernetes"]

    @classmethod
    def activate(cls) -> None:
        """Activate the Azure integration."""
        from zenml.integrations.azure import service_connectors  # noqa

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declares the flavors for the integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.azure.flavors import (
            AzureArtifactStoreFlavor,
            AzureMLOrchestratorFlavor,
            AzureMLStepOperatorFlavor,
        )

        return [
            AzureArtifactStoreFlavor,
            AzureMLStepOperatorFlavor,
            AzureMLOrchestratorFlavor,
        ]
