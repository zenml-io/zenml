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

from typing import Any, List, Optional

import sagemaker

from zenml.enums import StackComponentType, TrainingResourceFlavor
from zenml.repository import Repository
from zenml.stack import StackValidator
from zenml.stack.stack_component_class_registry import (
    register_stack_component_class,
)
from zenml.training_resources import BaseTrainingResource
from zenml.utils import docker_utils


@register_stack_component_class(
    component_type=StackComponentType.TRAINING_RESOURCE,
    component_flavor=TrainingResourceFlavor.SAGEMAKER,
)
class SagemakerTrainingResource(BaseTrainingResource):
    """Training resource to run a step on Sagemaker."""

    supports_local_execution = True
    supports_remote_execution = True

    role: str
    instance_type: str

    base_image: Optional[str] = None
    bucket: Optional[str] = None
    experiment_name: Optional[str] = None

    @property
    def flavor(self) -> TrainingResourceFlavor:
        """The training resource flavor."""
        return TrainingResourceFlavor.SAGEMAKER

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates that the stack contains a container registry."""
        return StackValidator(
            required_components={StackComponentType.CONTAINER_REGISTRY}
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
            build_context_path=str(repo.root),
            image_name=image_name,
            entrypoint=" ".join(entrypoint_command),
            requirements=set(requirements),
            base_image=self.base_image,
        )
        docker_utils.push_docker_image(image_name)
        return docker_utils.get_image_digest(image_name) or image_name

    def launch(
        self,
        pipeline_name: str,
        run_name: str,
        entrypoint_command: List[str],
        requirements: List[str],
    ) -> Any:
        """Launches a step on Sagemaker."""
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
