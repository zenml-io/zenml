#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.

#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:

#       https://www.apache.org/licenses/LICENSE-2.0

#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Functionality to deploy a ZenML stack to Azure."""

import re
from typing import ClassVar, Dict, List

from zenml.enums import StackDeploymentProvider
from zenml.stack_deployments.stack_deployment import ZenMLCloudStackDeployment


# TODO: this class just implements the regions list, and is not suitable for other
# deployment tasks.
class AZUREZenMLCloudStackDeployment(ZenMLCloudStackDeployment):
    """Azure ZenML Cloud Stack Deployment."""

    provider: ClassVar[StackDeploymentProvider] = StackDeploymentProvider.AZURE

    @classmethod
    def description(cls) -> str:
        """Return a description of the ZenML Cloud Stack Deployment.

        This will be displayed when the user is prompted to deploy
        the ZenML stack.

        Returns:
            A MarkDown description of the ZenML Cloud Stack Deployment.
        """
        # TODO: Implement this
        return ""

    @classmethod
    def instructions(cls) -> str:
        """Return instructions on how to deploy the ZenML stack to the specified cloud provider.

        This will be displayed before the user is prompted to deploy the ZenML
        stack.

        Returns:
            MarkDown instructions on how to deploy the ZenML stack to the
            specified cloud provider.
        """
        # TODO: Implement this
        return ""

    @classmethod
    def post_deploy_instructions(cls) -> str:
        """Return instructions on what to do after the deployment is complete.

        This will be displayed after the deployment is complete.

        Returns:
            MarkDown instructions on what to do after the deployment is
            complete.
        """
        # TODO: Implement this
        return ""

    @classmethod
    def integrations(cls) -> List[str]:
        """Return the ZenML integrations required for the stack.

        Returns:
            The list of ZenML integrations that need to be installed for the
            stack to be usable.
        """
        return ["azure"]

    @classmethod
    def permissions(cls) -> Dict[str, List[str]]:
        """Return the permissions granted to ZenML to access the cloud resources.

        Returns:
            The permissions granted to ZenML to access the cloud resources, as
            a dictionary grouping permissions by resource.
        """
        # TODO: Implement this
        return {}

    @classmethod
    def locations(cls) -> Dict[str, str]:
        """Return the locations where the ZenML stack can be deployed.

        Returns:
            The regions where the ZenML stack can be deployed as a map of region
            names to region descriptions.
        """
        # Based on `az account list-locations -o table` on 16.07.2024
        return {
            "(US) East US": "eastus",
            "(US) South Central US": "southcentralus",
            "(US) West US 2": "westus2",
            "(US) West US 3": "westus3",
            "(Asia Pacific) Australia East": "australiaeast",
            "(Asia Pacific) Southeast Asia": "southeastasia",
            "(Europe) North Europe": "northeurope",
            "(Europe) Sweden Central": "swedencentral",
            "(Europe) UK South": "uksouth",
            "(Europe) West Europe": "westeurope",
            "(US) Central US": "centralus",
            "(Africa) South Africa North": "southafricanorth",
            "(Asia Pacific) Central India": "centralindia",
            "(Asia Pacific) East Asia": "eastasia",
            "(Asia Pacific) Japan East": "japaneast",
            "(Asia Pacific) Korea Central": "koreacentral",
            "(Canada) Canada Central": "canadacentral",
            "(Europe) France Central": "francecentral",
            "(Europe) Germany West Central": "germanywestcentral",
            "(Europe) Italy North": "italynorth",
            "(Europe) Norway East": "norwayeast",
            "(Europe) Poland Central": "polandcentral",
            "(Europe) Spain Central": "spaincentral",
            "(Europe) Switzerland North": "switzerlandnorth",
            "(Mexico) Mexico Central": "mexicocentral",
            "(Middle East) UAE North": "uaenorth",
            "(South America) Brazil South": "brazilsouth",
            "(Middle East) Israel Central": "israelcentral",
            "(Middle East) Qatar Central": "qatarcentral",
            "(US) Central US (Stage)": "centralusstage",
            "(US) East US (Stage)": "eastusstage",
            "(US) East US 2 (Stage)": "eastus2stage",
            "(US) North Central US (Stage)": "northcentralusstage",
            "(US) South Central US (Stage)": "southcentralusstage",
            "(US) West US (Stage)": "westusstage",
            "(US) West US 2 (Stage)": "westus2stage",
            "(Asia Pacific) East Asia (Stage)": "eastasiastage",
            "(Asia Pacific) Southeast Asia (Stage)": "southeastasiastage",
            "(South America) Brazil US": "brazilus",
            "(US) East US 2": "eastus2",
            "(US) East US STG": "eastusstg",
            "(US) North Central US": "northcentralus",
            "(US) West US": "westus",
            "(Asia Pacific) Japan West": "japanwest",
            "(Asia Pacific) Jio India West": "jioindiawest",
            "(US) Central US EUAP": "centraluseuap",
            "(US) East US 2 EUAP": "eastus2euap",
            "(US) West Central US": "westcentralus",
            "(Africa) South Africa West": "southafricawest",
            "(Asia Pacific) Australia Central": "australiacentral",
            "(Asia Pacific) Australia Central 2": "australiacentral2",
            "(Asia Pacific) Australia Southeast": "australiasoutheast",
            "(Asia Pacific) Jio India Central": "jioindiacentral",
            "(Asia Pacific) Korea South": "koreasouth",
            "(Asia Pacific) South India": "southindia",
            "(Asia Pacific) West India": "westindia",
            "(Canada) Canada East": "canadaeast",
            "(Europe) France South": "francesouth",
            "(Europe) Germany North": "germanynorth",
            "(Europe) Norway West": "norwaywest",
            "(Europe) Switzerland West": "switzerlandwest",
            "(Europe) UK West": "ukwest",
            "(Middle East) UAE Central": "uaecentral",
            "(South America) Brazil Southeast": "brazilsoutheast",
        }

    @classmethod
    def skypilot_default_regions(cls) -> Dict[str, str]:
        """Returns the regions supported by default for the Skypilot.

        Returns:
            The regions supported by default for the Skypilot.
        """
        matcher = re.compile(r".*us\d*( |$)")
        return {
            k: v
            for k, v in cls.locations().items()
            if "(US)" in k and matcher.match(v)
        }
