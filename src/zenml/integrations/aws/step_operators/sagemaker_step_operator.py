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
"""Implementation of the Sagemaker Step Operator."""

from typing import TYPE_CHECKING, ClassVar, List, Optional

import sagemaker

from zenml.enums import StackComponentType
from zenml.integrations.aws import AWS_SAGEMAKER_STEP_OPERATOR_FLAVOR
from zenml.logger import get_logger
from zenml.stack import Stack, StackValidator
from zenml.step_operators import BaseStepOperator
from zenml.utils import deprecation_utils
from zenml.utils.pipeline_docker_image_builder import PipelineDockerImageBuilder

if TYPE_CHECKING:
    from zenml.config.pipeline_deployment import PipelineDeployment
    from zenml.config.step_run_info import StepRunInfo

logger = get_logger(__name__)

SAGEMAKER_DOCKER_IMAGE_KEY = "sagemaker_docker_image"
_ENTRYPOINT_ENV_VARIABLE = "__ZENML_ENTRYPOINT"


class SagemakerStepOperator(BaseStepOperator, PipelineDockerImageBuilder):
    """Step operator to run a step on Sagemaker.

    This class defines code that builds an image with the ZenML entrypoint
    to run using Sagemaker's Estimator.

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

    # Class Configuration
    FLAVOR: ClassVar[str] = AWS_SAGEMAKER_STEP_OPERATOR_FLAVOR

    _deprecation_validator = deprecation_utils.deprecate_pydantic_attributes(
        ("base_image", "docker_parent_image")
    )

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates that the stack contains a container registry.

        Returns:
            A validator that checks that the stack contains a container registry.
        """
        return StackValidator(
            required_components={StackComponentType.CONTAINER_REGISTRY},
        )

    def prepare_pipeline_deployment(
        self,
        deployment: "PipelineDeployment",
        stack: "Stack",
    ) -> None:
        """Build a Docker image and push it to the container registry.

        Args:
            deployment: The pipeline deployment configuration.
            stack: The stack on which the pipeline will be deployed.
        """
        steps_to_run = [
            step
            for step in deployment.steps.values()
            if step.config.step_operator == self.name
        ]
        if not steps_to_run:
            return

        image_digest = self.build_and_push_docker_image(
            deployment=deployment,
            stack=stack,
            entrypoint=f"${_ENTRYPOINT_ENV_VARIABLE}",
        )
        for step in steps_to_run:
            step.config.extra[SAGEMAKER_DOCKER_IMAGE_KEY] = image_digest

    def launch(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
    ) -> None:
        """Launches a step on SageMaker.

        Args:
            info: Information about the step run.
            entrypoint_command: Command that executes the step.
        """
        if not info.config.resource_settings.empty:
            logger.warning(
                "Specifying custom step resources is not supported for "
                "the SageMaker step operator. If you want to run this step "
                "operator on specific resources, you can do so by configuring "
                "a different instance type like this: "
                "`zenml step-operator update %s "
                "--instance_type=<INSTANCE_TYPE>`",
                self.name,
            )

        image_name = info.config.extra[SAGEMAKER_DOCKER_IMAGE_KEY]
        environment = {_ENTRYPOINT_ENV_VARIABLE: " ".join(entrypoint_command)}

        session = sagemaker.Session(default_bucket=self.bucket)
        estimator = sagemaker.estimator.Estimator(
            image_name,
            self.role,
            environment=environment,
            instance_count=1,
            instance_type=self.instance_type,
            sagemaker_session=session,
        )

        # Sagemaker doesn't allow any underscores in job/experiment/trial names
        sanitized_run_name = info.run_name.replace("_", "-")

        experiment_config = {}
        if self.experiment_name:
            experiment_config = {
                "ExperimentName": self.experiment_name,
                "TrialName": sanitized_run_name,
            }

        estimator.fit(
            wait=True,
            experiment_config=experiment_config,
            job_name=sanitized_run_name,
        )
