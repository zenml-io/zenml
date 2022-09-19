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

from typing import TYPE_CHECKING, Optional, Type

from zenml.integrations.aws import AWS_SAGEMAKER_STEP_OPERATOR_FLAVOR
from zenml.step_operators.base_step_operator import (
    BaseStepOperatorConfig,
    BaseStepOperatorFlavor,
)
from zenml.utils import deprecation_utils

if TYPE_CHECKING:
    from zenml.integrations.aws.step_operators import SagemakerStepOperator


class SagemakerStepOperatorConfig(BaseStepOperatorConfig):
    """Config for the Sagemaker step operator.

    Attributes:
        role: The role that has to be assigned to the jobs which are
            running in Sagemaker.
        instance_type: The type of the compute instance where jobs will run.
        base_image: The base image to use for building the docker
            image that will be executed.
        bucket: Name of the S3 bucket to use for storing artifacts
            from the job run. If not provided, a default bucket will be created
            based on the following format: "sagemaker-{region}-{aws-account-id}".
        experiment_name: The name for the experiment to which the job
            will be associated. If not provided, the job runs would be
            independent.
    """

    role: str
    instance_type: str
    base_image: Optional[str] = None
    bucket: Optional[str] = None
    experiment_name: Optional[str] = None

    _deprecation_validator = deprecation_utils.deprecate_pydantic_attributes(
        ("base_image", "docker_parent_image")
    )


class SagemakerStepOperatorFlavor(BaseStepOperatorFlavor):
    """Flavor for the Sagemaker step operator."""

    @property
    def name(self) -> str:
        return AWS_SAGEMAKER_STEP_OPERATOR_FLAVOR

    @property
    def config_class(self) -> Type[SagemakerStepOperatorConfig]:
        return SagemakerStepOperatorConfig

    @property
    def implementation_class(self) -> Type["SagemakerStepOperator"]:
        from zenml.integrations.aws.step_operators import SagemakerStepOperator

        return SagemakerStepOperator
