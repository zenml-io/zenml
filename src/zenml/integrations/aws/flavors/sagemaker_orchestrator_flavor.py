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
"""Amazon SageMaker orchestrator flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.config.base_settings import BaseSettings
from zenml.integrations.aws import AWS_SAGEMAKER_STEP_OPERATOR_FLAVOR
from zenml.orchestrators.base_orchestrator import BaseOrchestratorFlavor
from zenml.step_operators.base_step_operator import BaseStepOperatorConfig

if TYPE_CHECKING:
    from zenml.integrations.aws.orchestrators import SagemakerOrchestrator


class SagemakerOrchestratorSettings(BaseSettings):
    """Settings for the Sagemaker orchestrator."""

    step_instance_type: Optional[str] = None


class SagemakerOrchestratorConfig(  # type: ignore[misc] # https://github.com/pydantic/pydantic/issues/4173
    BaseStepOperatorConfig, SagemakerOrchestratorSettings
):
    """Config for the Sagemaker orchestrator.
    Attributes:
        default_instance_type: The instance type to use for the processing job.
        bucket: Name of the S3 bucket to use for storing artifacts
            from the job run. If not provided, a default bucket will be created
            based on the following format: "sagemaker-{region}-{aws-account-id}".
    """

    # 'ml.t3.medium' is the default instance for Sagemaker processing jobs
    default_instance_type: str = "ml.t3.medium"
    processor_role: Optional[str] = None
    bucket: Optional[str] = None

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


class SagemakerOrchestratorFlavor(BaseOrchestratorFlavor):
    """Flavor for the Sagemaker orchestrator."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return AWS_SAGEMAKER_STEP_OPERATOR_FLAVOR

    @property
    def config_class(self) -> Type[SagemakerOrchestratorConfig]:
        """Returns SagemakerOrchestratorConfig config class.

        Returns:
            The config class.
        """
        return SagemakerOrchestratorConfig

    @property
    def implementation_class(self) -> Type["SagemakerOrchestrator"]:
        """Implementation class.

        Returns:
            The implementation class.
        """
        from zenml.integrations.aws.orchestrators import SagemakerOrchestrator

        return SagemakerOrchestrator
