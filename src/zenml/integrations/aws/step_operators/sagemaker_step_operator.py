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

from typing import TYPE_CHECKING, ClassVar, List, Optional, Tuple

import sagemaker

from zenml.enums import StackComponentType
from zenml.integrations.aws import AWS_SAGEMAKER_STEP_OPERATOR_FLAVOR
from zenml.logger import get_logger
from zenml.repository import Repository
from zenml.runtime_configuration import RuntimeConfiguration
from zenml.stack import Stack, StackValidator
from zenml.step_operators import BaseStepOperator
from zenml.utils import deprecation_utils
from zenml.utils.pipeline_docker_image_builder import PipelineDockerImageBuilder

if TYPE_CHECKING:
    from zenml.config.docker_configuration import DockerConfiguration
    from zenml.config.resource_configuration import ResourceConfiguration


logger = get_logger(__name__)


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

        def _ensure_local_orchestrator(stack: Stack) -> Tuple[bool, str]:
            return (
                stack.orchestrator.FLAVOR == "local",
                "Local orchestrator is required",
            )

        return StackValidator(
            required_components={StackComponentType.CONTAINER_REGISTRY},
            custom_validation_function=_ensure_local_orchestrator,
        )

    def launch(
        self,
        pipeline_name: str,
        run_name: str,
        docker_configuration: "DockerConfiguration",
        entrypoint_command: List[str],
        resource_configuration: "ResourceConfiguration",
    ) -> None:
        """Launches a step on Sagemaker.

        Args:
            pipeline_name: Name of the pipeline which the step to be executed
                is part of.
            run_name: Name of the pipeline run which the step to be executed
                is part of.
            docker_configuration: The Docker configuration for this step.
            entrypoint_command: Command that executes the step.
            resource_configuration: The resource configuration for this step.
        """
        image_name = self.build_and_push_docker_image(
            pipeline_name=pipeline_name,
            docker_configuration=docker_configuration,
            stack=Repository().active_stack,
            runtime_configuration=RuntimeConfiguration(),
            entrypoint=" ".join(entrypoint_command),
        )

        if not resource_configuration.empty:
            logger.warning(
                "Specifying custom step resources is not supported for "
                "the SageMaker step operator. If you want to run this step "
                "operator on specific resources, you can do so by configuring "
                "a different instance type like this: "
                "`zenml step-operator update %s "
                "--instance_type=<INSTANCE_TYPE>`",
                self.name,
            )

        session = sagemaker.Session(default_bucket=self.bucket)
        estimator = sagemaker.estimator.Estimator(
            image_name,
            self.role,
            instance_count=1,
            instance_type=self.instance_type,
            sagemaker_session=session,
        )

        # Sagemaker doesn't allow any underscores in job/experiment/trial names
        sanitized_run_name = run_name.replace("_", "-")

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
