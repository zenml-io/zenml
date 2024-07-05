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

from typing import ClassVar, Dict, List, Tuple

from zenml.enums import StackDeploymentProvider
from zenml.stack_deployments.stack_deployment import ZenMLCloudStackDeployment

GCP_DEPLOYMENT_TYPE = "deployment-manager"


class GCPZenMLCloudStackDeployment(ZenMLCloudStackDeployment):
    """GCP ZenML Cloud Stack Deployment."""

    provider: ClassVar[StackDeploymentProvider] = StackDeploymentProvider.GCP
    deployment: ClassVar[str] = GCP_DEPLOYMENT_TYPE

    @classmethod
    def description(cls) -> str:
        """Return a description of the ZenML Cloud Stack Deployment.

        This will be displayed when the user is prompted to deploy
        the ZenML stack.

        Returns:
            A MarkDown description of the ZenML Cloud Stack Deployment.
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

The deployment parameters will be pre-filled with the necessary information to
connect ZenML to your GCP project, so you should only need to review and confirm
the stack.

After the Deployment Manager deployment is complete, you can return to the CLI
to view details about the associated ZenML stack automatically registered with
ZenML.

**NOTE**: The Deployment Manager deployment will create the following new
resources in your GCP project. Please ensure you have the necessary permissions
and are aware of any potential costs:

- A GCS bucket registered as a [ZenML artifact store](https://docs.zenml.io/stack-components/artifact-stores/gcp).
- A Google Artifact Registry registered as a [ZenML container registry](https://docs.zenml.io/stack-components/container-registries/gcp).
- Vertex AI registered as a [ZenML orchestrator](https://docs.zenml.io/stack-components/orchestrators/vertex).
- A GCP Service Account with the minimum necessary permissions to access the
above resources.
- An GCP Service Account access key used to give access to ZenML to connect to
the above resources through a [ZenML service connector](https://docs.zenml.io/how-to/auth-management/gcp-service-connector).

The Deployment Manager deployment will automatically create a GCP Service
Account secret key and will share it with ZenML to give it permission to access
the resources created by the stack. You can revoke these permissions at any time
by deleting the Deployment Manager deployment in the GCP Cloud Console.
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
            "ECR Repository": [
                "roles/artifactregistry.createOnPushWriter",
            ],
            "Vertex AI (Client)": [
                "roles/aiplatform.user",
            ],
            "Vertex AI (Jobs)": [
                "roles/aiplatform.serviceAgent",
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

    def deploy_url(
        self,
        zenml_server_url: str,
        zenml_server_api_token: str,
    ) -> Tuple[str, str]:
        """Return the URL to deploy the ZenML stack to the specified cloud provider.

        The URL should point to a cloud provider console where the user can
        deploy the ZenML stack and should include as many pre-filled parameters
        as possible.

        Args:
            zenml_server_url: The URL of the ZenML server.
            zenml_server_api_token: The API token to authenticate with the ZenML
                server.

        Returns:
            The URL to deploy the ZenML stack to the specified cloud provider
            and a text description of the URL.
        """
        params = dict(
            cloudshell_git_repo="https://github.com/zenml-io/zenml",
            cloudshell_workspace="infra/gcp",
            cloudshell_open_in_editor="gcp-gar-gcs-vertex.jinja,gcp-gar-gcs-vertex-config.yaml",
            cloudshell_tutorial="gcp-gar-gcs-vertex.md",
            ephemeral="true",
            # TODO: remove this before the branch is merged
            cloudshell_git_branch="feature/prd-482-gcp-stack-deployment",
        )
        # Encode the parameters as URL query parameters
        query_params = "&".join([f"{k}={v}" for k, v in params.items()])

        return (
            f"https://ssh.cloud.google.com/cloudshell/editor?{query_params}",
            "GCP Cloud Shell Console",
        )
