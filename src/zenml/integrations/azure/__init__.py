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
        "azure-keyvault-keys",
        "azure-keyvault-secrets",
        "azure-identity",
        "azureml-core==1.54.0.post1",
        "azure-mgmt-containerservice>=20.0.0",
        "azure-storage-blob==12.17.0",  # temporary fix for https://github.com/Azure/azure-sdk-for-python/issues/32056
        "kubernetes",
        "azure-ai-ml==1.18.0"
    ]
    REQUIREMENTS_IGNORED_ON_UNINSTALL = ["kubernetes"]

    @staticmethod
    def activate() -> None:
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
            AzureMLStepOperatorFlavor,
            AzureMLOrchestratorFlavor,
        )

        return [
            AzureArtifactStoreFlavor,
            AzureMLStepOperatorFlavor,
            AzureMLOrchestratorFlavor,
        ]


AzureIntegration.check_installation()
