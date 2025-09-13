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

from typing import TYPE_CHECKING, Any, Dict, Optional, Type, Union

from pydantic import Field

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
from zenml.utils import deprecation_utils

if TYPE_CHECKING:
    from zenml.integrations.aws.step_operators import AWSBatchStepOperator


class AWSBatchStepOperatorSettings(BaseSettings):
    """Settings for the Sagemaker step operator."""

    instance_type: Optional[str] = Field(
        'optimal',
        description="The instance type for AWS Batch to use for the step" \
        " execution. Example: 'm5.xlarge'",
    )
    environment: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables to pass to the container during " \
            "execution. Example: {'LOG_LEVEL': 'INFO', 'DEBUG_MODE': 'False'}",
    )
    timeout_seconds: int = Field(
        default=120,
        description="The number of seconds before AWS Batch times out the job."
    )

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
        "",
        description="The ECS execution role required to execute the AWS Batch" \
        " jobs as an ECS tasks."
    )
    job_role: str = Field(
        "",
        description="The ECS job role required by the container runtime inside" \
        "the ECS task."
    )
    job_queue_name: str = Field(
        description="The AWS Batch job queue to submit AWS Batch jobs to."
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
