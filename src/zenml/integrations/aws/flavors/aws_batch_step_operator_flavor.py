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
"""Amazon SageMaker step operator flavor."""

from typing import TYPE_CHECKING, Dict, Optional, Type, List, Union

from pydantic import Field, PositiveInt, field_validator
from zenml.utils.secret_utils import SecretField
from zenml.config.base_settings import BaseSettings
from zenml.integrations.aws import (
    AWS_RESOURCE_TYPE,
    AWS_BATCH_STEP_OPERATOR_FLAVOR,
)
from zenml.models import ServiceConnectorRequirements
from zenml.step_operators.base_step_operator import (
    BaseStepOperatorConfig,
    BaseStepOperatorFlavor,
)

if TYPE_CHECKING:
    from zenml.integrations.aws.step_operators import AWSBatchStepOperator


class AWSBatchStepOperatorSettings(BaseSettings):
    """Settings for the Sagemaker step operator."""

    environment: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables to pass to the container during " \
            "execution. Example: {'LOG_LEVEL': 'INFO', 'DEBUG_MODE': 'False'}",
    )
    job_queue_name: str = Field(
        default="",
        description="The AWS Batch job queue to submit the step AWS Batch job"
         " to. If not provided, falls back to the default job queue name "
         "specified at stack registration time."
    )
    platform_capability: str = Field(
        default="FARGATE",
        description="The AWS Batch platform capability for the step AWS Batch "
        "job to be orchestrated with. Defaults to 'FARGATE'."
    )
    timeout_seconds: PositiveInt = Field(
        default=3600,
        description="The number of seconds before AWS Batch times out the job."
    )

    @field_validator("platform_capability")
    def validate_platform_capability(cls, value):
        if value not in ["FARGATE","EC2"]:
            raise ValueError(f"Invalid platform capability {value}. Must be "
                             "either 'FARGATE' or 'EC2'")
        
        return value



class AWSBatchStepOperatorConfig(
    BaseStepOperatorConfig, AWSBatchStepOperatorSettings
):
    """Config for the AWS Batch step operator. 
    
    Note: We use ECS as a backend (not EKS), and EC2 as a compute engine (not
    Fargate). This is because
     - users can avoid the complexity of setting up an EKS cluster, and
     - we can AWS Batch multinode type job support later, which requires EC2
    """

    execution_role: str = Field(
        description="The IAM role arn of the ECS execution role."
    )
    job_role: str = Field(
        description="The IAM role arn of the ECS job role."
    )
    default_job_queue_name: str = Field(
        description="The default AWS Batch job queue to submit AWS Batch jobs to."
    )
    aws_access_key_id: Optional[str] = SecretField(
        default=None,
        description="The AWS access key ID to use to authenticate to AWS. "
        "If not provided, the value from the default AWS config will be used.",
    )
    aws_secret_access_key: Optional[str] = SecretField(
        default=None,
        description="The AWS secret access key to use to authenticate to AWS. "
        "If not provided, the value from the default AWS config will be used.",
    )
    aws_profile: Optional[str] = Field(
        None,
        description="The AWS profile to use for authentication if not using "
        "service connectors or explicit credentials. If not provided, the "
        "default profile will be used.",
    )
    aws_auth_role_arn: Optional[str] = Field(
        None,
        description="The ARN of an intermediate IAM role to assume when "
        "authenticating to AWS.",
    )
    region: Optional[str] = Field(
        None,
        description="The AWS region where the processing job will be run. "
        "If not provided, the value from the default AWS config will be used.",
    )

    @property
    def is_remote(self) -> bool:
        """Checks if this stack component is running remotely.

        This designation is used to determine if the stack component can be
        used with a local ZenML database or if it requires a remote ZenML
        server.

        Returns:
            True if this config is for a remote component, False otherwise.
        """
        return True


class AWSBatchStepOperatorFlavor(BaseStepOperatorFlavor):
    """Flavor for the AWS Batch step operator."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return AWS_BATCH_STEP_OPERATOR_FLAVOR

    @property
    def service_connector_requirements(
        self,
    ) -> Optional[ServiceConnectorRequirements]:
        """Service connector resource requirements for service connectors.

        Specifies resource requirements that are used to filter the available
        service connector types that are compatible with this flavor.

        Returns:
            Requirements for compatible service connectors, if a service
            connector is required for this flavor.
        """
        return ServiceConnectorRequirements(resource_type=AWS_RESOURCE_TYPE)

    @property
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/step_operator/aws_batch.png"

    @property
    def config_class(self) -> Type[AWSBatchStepOperatorConfig]:
        """Returns BatchStepOperatorConfig config class.

        Returns:
            The config class.
        """
        return AWSBatchStepOperatorConfig

    @property
    def implementation_class(self) -> Type["AWSBatchStepOperator"]:
        """Implementation class.

        Returns:
            The implementation class.
        """
        from zenml.integrations.aws.step_operators import AWSBatchStepOperator

        return AWSBatchStepOperator
