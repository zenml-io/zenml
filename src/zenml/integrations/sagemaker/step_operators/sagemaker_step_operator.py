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

from typing import ClassVar, List, Optional, Tuple

import sagemaker

from zenml.enums import StackComponentType
from zenml.integrations.sagemaker import SAGEMAKER_STEP_OPERATOR_FLAVOR
from zenml.repository import Repository
from zenml.stack import Stack, StackValidator
from zenml.step_operators import BaseStepOperator
from zenml.utils import docker_utils
from zenml.utils.source_utils import get_source_root_path


class SagemakerStepOperator(BaseStepOperator):
    """Step operator to run a step on Sagemaker.

    This class defines code that builds an image with the ZenML entrypoint
    to run using Sagemaker's Estimator.

    Attributes:
        role: The role that has to be assigned to the jobs which are
            running in Sagemaker.
        instance_type: The type of the compute instance where jobs will run.
        base_image: [Optional] The base image to use for building the docker
            image that will be executed.
        bucket: [Optional] Name of the S3 bucket to use for storing artifacts
            from the job run. If not provided, a default bucket will be created
            based on the following format: "sagemaker-{region}-{aws-account-id}".
        experiment_name: [Optional] The name for the experiment to which the job
            will be associated. If not provided, the job runs would be
            independent.
    """

    role: str
    instance_type: str

    base_image: Optional[str] = None
    bucket: Optional[str] = None
    experiment_name: Optional[str] = None

    # Class Configuration
    FLAVOR: ClassVar[str] = SAGEMAKER_STEP_OPERATOR_FLAVOR

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates that the stack contains a container registry."""

        def _ensure_local_orchestrator(stack: Stack) -> Tuple[bool, str]:
            return (
                stack.orchestrator.FLAVOR == "local",
                "Local orchestrator is required",
            )

        return StackValidator(
            required_components={StackComponentType.CONTAINER_REGISTRY},
            custom_validation_function=_ensure_local_orchestrator,
        )

    def _build_docker_image(
        self,
        pipeline_name: str,
        requirements: List[str],
        entrypoint_command: List[str],
    ) -> str:
        repo = Repository()
        container_registry = repo.active_stack.container_registry

        if not container_registry:
            raise RuntimeError("Missing container registry")

        registry_uri = container_registry.uri.rstrip("/")
        image_name = f"{registry_uri}/zenml-sagemaker:{pipeline_name}"

        docker_utils.build_docker_image(
            build_context_path=get_source_root_path(),
            image_name=image_name,
            entrypoint=" ".join(entrypoint_command),
            requirements=set(requirements),
            base_image=self.base_image,
        )
        container_registry.push_image(image_name)
        return docker_utils.get_image_digest(image_name) or image_name

    def launch(
        self,
        pipeline_name: str,
        run_name: str,
        requirements: List[str],
        entrypoint_command: List[str],
    ) -> None:
        """Launches a step on Sagemaker.

        Args:
            pipeline_name: Name of the pipeline which the step to be executed
                is part of.
            run_name: Name of the pipeline run which the step to be executed
                is part of.
            entrypoint_command: Command that executes the step.
            requirements: List of pip requirements that must be installed
                inside the step operator environment.
        """
        image_name = self._build_docker_image(
            pipeline_name=pipeline_name,
            requirements=requirements,
            entrypoint_command=entrypoint_command,
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
