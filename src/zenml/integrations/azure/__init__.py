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
AZURE_SECRETS_MANAGER_FLAVOR = "azure"
AZUREML_STEP_OPERATOR_FLAVOR = "azureml"


class AzureIntegration(Integration):
    """Definition of Azure integration for ZenML."""

    NAME = AZURE
    REQUIREMENTS = [
        "adlfs==2021.10.0",
        "azure-keyvault-keys",
        "azure-keyvault-secrets",
        "azure-identity==1.10.0",
        "azureml-core==1.48.0",
    ]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declares the flavors for the integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.azure.flavors import (
            AzureArtifactStoreFlavor,
            AzureMLStepOperatorFlavor,
            AzureSecretsManagerFlavor,
        )

        return [
            AzureArtifactStoreFlavor,
            AzureSecretsManagerFlavor,
            AzureMLStepOperatorFlavor,
        ]


AzureIntegration.check_installation()
