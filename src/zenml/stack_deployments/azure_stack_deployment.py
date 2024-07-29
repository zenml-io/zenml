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
from zenml.models import StackDeploymentConfig
from zenml.stack_deployments.stack_deployment import ZenMLCloudStackDeployment


class AZUREZenMLCloudStackDeployment(ZenMLCloudStackDeployment):
    """Azure ZenML Cloud Stack Deployment."""

    provider: ClassVar[StackDeploymentProvider] = StackDeploymentProvider.AZURE
    deployment: ClassVar[str] = "terraform"

    @classmethod
    def description(cls) -> str:
        """Return a description of the ZenML Cloud Stack Deployment.

        This will be displayed when the user is prompted to deploy
        the ZenML stack.

        Returns:
            A MarkDown description of the ZenML Cloud Stack Deployment.
        """
        return """
Provision and register a basic Azure ZenML stack authenticated and connected to
all the necessary cloud infrastructure resources required to run pipelines in
Azure.
"""

    @classmethod
    def instructions(cls) -> str:
        """Return instructions on how to deploy the ZenML stack to the specified cloud provider.

        This will be displayed before the user is prompted to deploy the ZenML
        stack.

        Returns:
            MarkDown instructions on how to deploy the ZenML stack to the
            specified cloud provider.
        """
        return """
You will be redirected to an Azure Cloud Shell console in your browser where
you'll be asked to log into your Azure project and then use
[the Azure ZenML Stack Terraform module](https://registry.terraform.io/modules/zenml-io/zenml-stack/azure)
to provision the necessary cloud resources for ZenML.

**NOTE**: The Azure ZenML Stack Terraform module will create the following new
resources in your Azure subscription. Please ensure you have the necessary
permissions and are aware of any potential costs:

- An Azure Resource Group to contain all the resources required for the ZenML stack
- An Azure Storage Account and Blob Storage Container registered as a [ZenML artifact store](https://docs.zenml.io/stack-components/artifact-stores/azure).
- An Azure Container Registry registered as a [ZenML container registry](https://docs.zenml.io/stack-components/container-registries/azure).
- SkyPilot will be registered as a [ZenML orchestrator](https://docs.zenml.io/stack-components/orchestrators/skypilot-vm) and used to run pipelines in your Azure subscription.
- An Azure Service Principal with the minimum necessary permissions to access
the above resources.
- An Azure Service Principal client secret used to give access to ZenML to
connect to the above resources through a [ZenML service connector](https://docs.zenml.io/how-to/auth-management/azure-service-connector).

The Azure ZenML Stack Terraform module will automatically create an Azure
Service Principal client secret and will share it with ZenML to give it
permission to access the resources created by the stack. You can revoke these
permissions at any time by deleting the Service Principal in your Azure
subscription.

**Estimated costs**

A small training job would cost around: $0.60

These are rough estimates and actual costs may vary based on your usage and specific Azure pricing. 
Some services may be eligible for the Azure Free Tier. Use [the Azure Pricing Calculator](https://azure.microsoft.com/en-us/pricing/calculator)
for a detailed estimate based on your usage.


💡 **After the Terraform deployment is complete, you can close the Cloud
Shell session and return to the CLI to view details about the associated ZenML
stack automatically registered with ZenML.**
"""

    @classmethod
    def post_deploy_instructions(cls) -> str:
        """Return instructions on what to do after the deployment is complete.

        This will be displayed after the deployment is complete.

        Returns:
            MarkDown instructions on what to do after the deployment is
            complete.
        """
        return """
The ZenML stack has been successfully deployed and registered. You can delete
the provisioned Service Principal and Resource Group at any time to revoke
ZenML's access to your Azure subscription.
"""

    @classmethod
    def integrations(cls) -> List[str]:
        """Return the ZenML integrations required for the stack.

        Returns:
            The list of ZenML integrations that need to be installed for the
            stack to be usable.
        """
        return ["azure", "skypilot_azure"]

    @classmethod
    def permissions(cls) -> Dict[str, List[str]]:
        """Return the permissions granted to ZenML to access the cloud resources.

        Returns:
            The permissions granted to ZenML to access the cloud resources, as
            a dictionary grouping permissions by resource.
        """
        return {
            "Storage Account": [
                "Storage Blob Data Contributor",
            ],
            "Container Registry": [
                "AcrPull",
                "AcrPush",
                "Contributor",
            ],
            "Subscription": [
                "Owner (required by SkyPilot)",
            ],
        }

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

    def get_deployment_config(
        self,
    ) -> StackDeploymentConfig:
        """Return the configuration to deploy the ZenML stack to the specified cloud provider.

        The configuration should include:

        * a cloud provider console URL where the user will be redirected to
        deploy the ZenML stack. The URL should include as many pre-filled
        URL query parameters as possible.
        * a textual description of the URL
        * some deployment providers may require additional configuration
        parameters or scripts to be passed to the cloud provider in addition to
        the deployment URL query parameters. Where that is the case, this method
        should also return a string that the user can copy and paste into the
        cloud provider console to deploy the ZenML stack (e.g. a set of
        environment variables, YAML configuration snippet, bash or Terraform
        script etc.).

        Returns:
            The configuration or script to deploy the ZenML stack to the
            specified cloud provider.
        """
        config = f"""module "zenml_stack" {{
    source  = "zenml-io/zenml-stack/azure"

    location = "{self.location or "eastus"}"
    zenml_server_url = "{self.zenml_server_url}"
    zenml_api_key = ""
    zenml_api_token = "{self.zenml_server_api_token}"
    zenml_stack_name = "{self.stack_name}"
}}
output "zenml_stack_id" {{
    value = module.zenml_stack_id
}}
output "zenml_stack_name" {{
    value = module.zenml_stack_name
}}"""
        instructions = """
1. The Azure Cloud Shell console will open in your browser.
2. Create a file named `main.tf` in the Cloud Shell and copy and paste the
Terraform configuration below into it.
3. Run `terraform init` to initialize the Terraform configuration.
4. Run `terraform apply` to deploy the ZenML stack to Azure.
"""

        return StackDeploymentConfig(
            deployment_url="https://shell.azure.com",
            deployment_url_text="Azure Cloud Shell Console",
            configuration=config,
            instructions=instructions,
        )
