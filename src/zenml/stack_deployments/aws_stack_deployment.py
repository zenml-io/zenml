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
"""Functionality to deploy a ZenML stack to AWS."""

from typing import ClassVar, Dict, List, Optional

from zenml.enums import StackDeploymentProvider
from zenml.models import StackDeploymentConfig
from zenml.stack_deployments.constants import (
    TERRAFORM_AWS_MODULE_VERSION_SPEC,
    TERRAFORM_PROVIDER_VERSION_SPEC,
)
from zenml.stack_deployments.stack_deployment import (
    STACK_DEPLOYMENT_TERRAFORM,
    ZenMLCloudStackDeployment,
)
from zenml.utils.string_utils import random_str

AWS_DEPLOYMENT_TYPE = "cloud-formation"


class AWSZenMLCloudStackDeployment(ZenMLCloudStackDeployment):
    """AWS ZenML Cloud Stack Deployment."""

    provider: ClassVar[StackDeploymentProvider] = StackDeploymentProvider.AWS
    deployment: ClassVar[str] = AWS_DEPLOYMENT_TYPE

    @classmethod
    def description(cls) -> str:
        """Return a description of the ZenML Cloud Stack Deployment.

        This will be displayed when the user is prompted to deploy
        the ZenML stack.

        Returns:
            A MarkDown description of the ZenML Cloud Stack Deployment.
        """
        return """
Provision and register a basic AWS ZenML stack authenticated and connected to
all the necessary cloud infrastructure resources required to run pipelines in
AWS.
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
You will be redirected to the AWS console in your browser where you'll be asked
to log into your AWS account and create a CloudFormation ZenML stack. The stack
parameters will be pre-filled with the necessary information to connect ZenML to
your AWS account, so you should only need to review and confirm the stack.

**NOTE**: The CloudFormation stack will create the following new resources in
your AWS account. Please ensure you have the necessary permissions and are aware
of any potential costs:

- An S3 bucket registered as a [ZenML artifact store](https://docs.zenml.io/stack-components/artifact-stores/s3).
- An ECR repository registered as a [ZenML container registry](https://docs.zenml.io/stack-components/container-registries/aws).
- Sagemaker registered as a [ZenML orchestrator](https://docs.zenml.io/stack-components/orchestrators/sagemaker)
as well as a [ZenML step operator](https://docs.zenml.io/stack-components/step-operators/sagemaker).
- A CodeBuild project registered as a [ZenML image builder](https://docs.zenml.io/stack-components/image-builder/aws).
- An IAM user and IAM role with the minimum necessary permissions to access the
above resources.
- An AWS access key used to give access to ZenML to connect to the above
resources through a [ZenML service connector](https://docs.zenml.io/how-to/auth-management/aws-service-connector).

The CloudFormation stack will automatically create an AWS secret key and
will share it with ZenML to give it permission to access the resources created
by the stack. You can revoke these permissions at any time by deleting the
CloudFormation stack.

**Estimated costs**

A small training job would cost around: $0.60

These are rough estimates and actual costs may vary based on your usage and specific AWS pricing. 
Some services may be eligible for the AWS Free Tier. Use [the AWS Pricing Calculator](https://calculator.aws)
for a detailed estimate based on your usage.

💡 **After the CloudFormation stack is deployed, you can return to the CLI to
view details about the associated ZenML stack automatically registered with
ZenML.**
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
the CloudFormation at any time to revoke ZenML's access to your AWS account and
to clean up the resources created by the stack by using the AWS CloudFormation
console.
"""

    @classmethod
    def integrations(cls) -> List[str]:
        """Return the ZenML integrations required for the stack.

        Returns:
            The list of ZenML integrations that need to be installed for the
            stack to be usable.
        """
        return [
            "aws",
            "s3",
        ]

    @classmethod
    def permissions(cls) -> Dict[str, List[str]]:
        """Return the permissions granted to ZenML to access the cloud resources.

        Returns:
            The permissions granted to ZenML to access the cloud resources, as
            a dictionary grouping permissions by resource.
        """
        return {
            "S3 Bucket": [
                "s3:ListBucket",
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:GetBucketVersioning",
                "s3:ListBucketVersions",
                "s3:DeleteObjectVersion",
            ],
            "ECR Repository": [
                "ecr:DescribeRepositories",
                "ecr:ListRepositories",
                "ecr:DescribeRegistry",
                "ecr:BatchGetImage",
                "ecr:DescribeImages",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload",
                "ecr:PutImage",
                "ecr:GetAuthorizationToken",
            ],
            "CloudBuild (Client)": [
                "codebuild:CreateProject",
                "codebuild:BatchGetBuilds",
            ],
            "CloudBuild (Service)": [
                "s3:GetObject",
                "s3:GetObjectVersion",
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "ecr:BatchGetImage",
                "ecr:DescribeImages",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload",
                "ecr:PutImage",
                "ecr:GetAuthorizationToken",
            ],
            "SageMaker (Client)": [
                "sagemaker:CreatePipeline",
                "sagemaker:StartPipelineExecution",
                "sagemaker:DescribePipeline",
                "sagemaker:DescribePipelineExecution",
            ],
            "SageMaker (Jobs)": [
                "AmazonSageMakerFullAccess",
            ],
        }

    @classmethod
    def locations(cls) -> Dict[str, str]:
        """Return the locations where the ZenML stack can be deployed.

        Returns:
            The regions where the ZenML stack can be deployed as a map of region
            names to region descriptions.
        """
        # Return a list of all possible AWS regions

        # Based on the AWS regions listed at
        # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html
        return {
            "Africa (Cape Town)": "af-south-1",
            "Asia Pacific (Hong Kong)": "ap-east-1",
            "Asia Pacific (Hyderabad)": "ap-south-2",
            "Asia Pacific (Jakarta)": "ap-southeast-3",
            "Asia Pacific (Melbourne)": "ap-southeast-4",
            "Asia Pacific (Mumbai)": "ap-south-1",
            "Asia Pacific (Osaka)": "ap-northeast-3",
            "Asia Pacific (Seoul)": "ap-northeast-2",
            "Asia Pacific (Singapore)": "ap-southeast-1",
            "Asia Pacific (Sydney)": "ap-southeast-2",
            "Asia Pacific (Tokyo)": "ap-northeast-1",
            "Canada (Central)": "ca-central-1",
            "Canada West (Calgary)": "ca-west-1",
            "Europe (Frankfurt)": "eu-central-1",
            "Europe (Ireland)": "eu-west-1",
            "Europe (London)": "eu-west-2",
            "Europe (Milan)": "eu-south-1",
            "Europe (Paris)": "eu-west-3",
            "Europe (Spain)": "eu-south-2",
            "Europe (Stockholm)": "eu-north-1",
            "Europe (Zurich)": "eu-central-2",
            "Israel (Tel Aviv)": "il-central-1",
            "Middle East (Bahrain)": "me-south-1",
            "Middle East (UAE)": "me-central-1",
            "South America (São Paulo)": "sa-east-1",
            "US East (Ohio)": "us-east-2",
            "US East (N. Virginia)": "us-east-1",
            "US West (N. California)": "us-west-1",
            "US West (Oregon)": "us-west-2",
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
        * a Terraform script used to deploy the ZenML stack
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
        params = dict(
            stackName=self.stack_name,
            templateURL="https://zenml-cf-templates.s3.eu-central-1.amazonaws.com/aws-ecr-s3-sagemaker.yaml",
            param_ResourceName=f"zenml-{random_str(6).lower()}",
            param_ZenMLServerURL=self.zenml_server_url,
            param_ZenMLServerAPIToken=self.zenml_server_api_token,
            param_CodeBuild="true",
        )
        # Encode the parameters as URL query parameters
        query_params = "&".join([f"{k}={v}" for k, v in params.items()])

        region = ""
        if self.location:
            region = f"region={self.location}"

        url = (
            f"https://console.aws.amazon.com/cloudformation/home?"
            f"{region}#/stacks/create/review?{query_params}"
        )

        config: Optional[str] = None
        if self.deployment_type == STACK_DEPLOYMENT_TERRAFORM:
            config = f"""terraform {{
    required_providers {{
        aws = {{
            source  = "hashicorp/aws"
        }}
        zenml = {{
            source = "zenml-io/zenml"
            version = "{TERRAFORM_PROVIDER_VERSION_SPEC}"
        }}
    }}
}}

provider "aws" {{
    region = "{self.location or "eu-central-1"}"
}}

provider "zenml" {{
    server_url = "{self.zenml_server_url}"
    api_token = "{self.zenml_server_api_token}"
}}

module "zenml_stack" {{
    source  = "zenml-io/zenml-stack/aws"
    version = "{TERRAFORM_AWS_MODULE_VERSION_SPEC}"
    zenml_stack_name = "{self.stack_name}"
    zenml_stack_deployment = "{self.deployment_type}"
}}
output "zenml_stack_id" {{
    value = module.zenml_stack.zenml_stack_id
}}
output "zenml_stack_name" {{
    value = module.zenml_stack.zenml_stack_name
}}"""

        return StackDeploymentConfig(
            deployment_url=url,
            deployment_url_text="AWS CloudFormation Console",
            configuration=config,
        )
