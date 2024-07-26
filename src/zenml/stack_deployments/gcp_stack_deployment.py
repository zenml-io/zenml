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
"""Functionality to deploy a ZenML stack to GCP."""

import re
from typing import ClassVar, Dict, List

from zenml.enums import StackDeploymentProvider
from zenml.models import StackDeploymentConfig
from zenml.stack_deployments.stack_deployment import ZenMLCloudStackDeployment

GCP_DEPLOYMENT_TYPE = "deployment-manager"


class GCPZenMLCloudStackDeployment(ZenMLCloudStackDeployment):
    """GCP ZenML Pro Stack Deployment."""

    provider: ClassVar[StackDeploymentProvider] = StackDeploymentProvider.GCP
    deployment: ClassVar[str] = GCP_DEPLOYMENT_TYPE

    @classmethod
    def description(cls) -> str:
        """Return a description of the ZenML Pro Stack Deployment.

        This will be displayed when the user is prompted to deploy
        the ZenML stack.

        Returns:
            A MarkDown description of the ZenML Pro Stack Deployment.
        """
        return """
Provision and register a basic GCP ZenML stack authenticated and connected to
all the necessary cloud infrastructure resources required to run pipelines in
GCP.
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
You will be redirected to a GCP Cloud Shell console in your browser where you'll
be asked to log into your GCP project and then create a Deployment Manager
deployment to provision the necessary cloud resources for ZenML.

**NOTE**: The Deployment Manager deployment will create the following new
resources in your GCP project. Please ensure you have the necessary permissions
and are aware of any potential costs:

- A GCS bucket registered as a [ZenML artifact store](https://docs.zenml.io/stack-components/artifact-stores/gcp).
- A Google Artifact Registry registered as a [ZenML container registry](https://docs.zenml.io/stack-components/container-registries/gcp).
- Vertex AI registered as a [ZenML orchestrator](https://docs.zenml.io/stack-components/orchestrators/vertex).
- GCP Cloud Build registered as a [ZenML image builder](https://docs.zenml.io/stack-components/image-builders/gcp).
- A GCP Service Account with the minimum necessary permissions to access the
above resources.
- An GCP Service Account access key used to give access to ZenML to connect to
the above resources through a [ZenML service connector](https://docs.zenml.io/how-to/auth-management/gcp-service-connector).

The Deployment Manager deployment will automatically create a GCP Service
Account secret key and will share it with ZenML to give it permission to access
the resources created by the stack. You can revoke these permissions at any time
by deleting the Deployment Manager deployment in the GCP Cloud Console.

**Estimated costs**

A small training job would cost around: $0.60

These are rough estimates and actual costs may vary based on your usage and specific GCP pricing. 
Some services may be eligible for the GCP Free Tier. Use [the GCP Pricing Calculator](https://cloud.google.com/products/calculator)
for a detailed estimate based on your usage.

⚠️  **The Cloud Shell session will warn you that the ZenML GitHub repository is
untrusted. We recommend that you review [the contents of the repository](https://github.com/zenml-io/zenml/tree/main/infra/gcp)
and then check the `Trust repo` checkbox to proceed with the deployment,
otherwise the Cloud Shell session will not be authenticated to access your
GCP projects. You will also get a chance to review the scripts that will be
executed in the Cloud Shell session before proceeding.**

💡 **After the Deployment Manager deployment is complete, you can close the Cloud
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
the Deployment Manager deployment at any time to revoke ZenML's access to your
GCP project and to clean up the resources created by the stack by using
[the GCP Cloud Console](https://console.cloud.google.com/dm/deployments).
"""

    @classmethod
    def integrations(cls) -> List[str]:
        """Return the ZenML integrations required for the stack.

        Returns:
            The list of ZenML integrations that need to be installed for the
            stack to be usable.
        """
        return [
            "gcp",
        ]

    @classmethod
    def permissions(cls) -> Dict[str, List[str]]:
        """Return the permissions granted to ZenML to access the cloud resources.

        Returns:
            The permissions granted to ZenML to access the cloud resources, as
            a dictionary grouping permissions by resource.
        """
        return {
            "GCS Bucket": [
                "roles/storage.objectUser",
            ],
            "GCP Artifact Registry": [
                "roles/artifactregistry.createOnPushWriter",
            ],
            "Vertex AI (Client)": [
                "roles/aiplatform.user",
            ],
            "Vertex AI (Jobs)": [
                "roles/aiplatform.serviceAgent",
            ],
            "Cloud Build (Client)": [
                "roles/cloudbuild.builds.editor",
            ],
        }

    @classmethod
    def locations(cls) -> Dict[str, str]:
        """Return the locations where the ZenML stack can be deployed.

        Returns:
            The regions where the ZenML stack can be deployed as a map of region
            names to region descriptions.
        """
        # Return a list of all possible GCP regions

        # Based on the AWS regions listed at
        # https://cloud.google.com/about/locations
        return {
            "Africa (Johannesburg)": "africa-south1",
            "Asia Pacific (Taiwan)": "asia-east1",
            "Asia Pacific (Hong Kong)": "asia-east2",
            "Asia Pacific (Tokyo)": "asia-northeast1",
            "Asia Pacific (Osaka)": "asia-northeast2",
            "Asia Pacific (Seoul)": "asia-northeast3",
            "Asia Pacific (Mumbai)": "asia-south1",
            "Asia Pacific (Delhi)": "asia-south2",
            "Asia Pacific (Singapore)": "asia-southeast1",
            "Asia Pacific (Jakarta)": "asia-southeast2",
            "Australia (Sydney)": "australia-southeast1",
            "Australia (Melbourne)": "australia-southeast2",
            "Europe (Belgium)": "europe-west1",
            "Europe (London)": "europe-west2",
            "Europe (Frankfurt)": "europe-west3",
            "Europe (Netherlands)": "europe-west4",
            "Europe (Zurich)": "europe-west6",
            "Europe (Milan)": "europe-west8",
            "Europe (Paris)": "europe-west9",
            "Europe (Berlin)": "europe-west10",
            "Europe (Turin)": "europe-west12",
            "Europe (Warsaw)": "europe-central2",
            "Europe (Finland)": "europe-north1",
            "Europe (Madrid)": "europe-southwest1",
            "Middle East (Doha)": "me-central1",
            "Middle East (Dubai)": "me-central2",
            "Middle East (Tel Aviv)": "me-west1",
            "North America (Montreal)": "northamerica-northeast1",
            "North America (Toronto)": "northamerica-northeast2",
            "South America (Sao Paulo)": "southamerica-east1",
            "South America (Santiago)": "southamerica-west1",
            "US Central (Iowa)": "us-central1",
            "US East (South Carolina)": "us-east1",
            "US East (Northern Virginia)": "us-east4",
            "US East (Columbus)": "us-east5",
            "US South (Dallas)": "us-south1",
            "US West (Oregon)": "us-west1",
            "US West (Los Angeles)": "us-west2",
            "US West (Salt Lake City)": "us-west3",
            "US West (Las Vegas)": "us-west4",
        }

    @classmethod
    def skypilot_default_regions(cls) -> Dict[str, str]:
        """Returns the regions supported by default for the Skypilot.

        Returns:
            The regions supported by default for the Skypilot.
        """
        matcher = re.compile(r"us-.*")
        return {k: v for k, v in cls.locations().items() if matcher.match(v)}

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
        parameters to be passed to the cloud provider in addition to the
        deployment URL query parameters. Where that is the case, this method
        should also return a string that the user can copy and paste into the
        cloud provider console to deploy the ZenML stack (e.g. a set of
        environment variables, or YAML configuration snippet etc.).

        Returns:
            The configuration to deploy the ZenML stack to the specified cloud
            provider.
        """
        params = dict(
            cloudshell_git_repo="https://github.com/zenml-io/zenml",
            cloudshell_workspace="infra/gcp",
            cloudshell_open_in_editor="gcp-gar-gcs-vertex.jinja,gcp-gar-gcs-vertex-deploy.sh",
            cloudshell_tutorial="gcp-gar-gcs-vertex.md",
            ephemeral="true",
        )
        # Encode the parameters as URL query parameters
        query_params = "&".join([f"{k}={v}" for k, v in params.items()])
        url = (
            f"https://shell.cloud.google.com/cloudshell/editor?{query_params}"
        )

        config = f"""
### BEGIN CONFIGURATION ###
ZENML_STACK_NAME={self.stack_name}
ZENML_STACK_REGION={self.location or "europe-west3"}
ZENML_SERVER_URL={self.zenml_server_url}
ZENML_SERVER_API_TOKEN={self.zenml_server_api_token}
### END CONFIGURATION ###"""

        return StackDeploymentConfig(
            deployment_url=url,
            deployment_url_text="GCP Cloud Shell Console",
            configuration=config,
        )
