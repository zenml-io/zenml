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
from typing import TYPE_CHECKING, List

from tfx.proto.orchestration import pipeline_pb2

import zenml
from zenml.logger import get_logger
from zenml.repository import Repository
from zenml.utils import docker_utils
from zenml.utils.source_utils import get_source_root_path

if TYPE_CHECKING:
    from zenml.stack import Stack

logger = get_logger(__name__)


class SeldonCustomDeployer:
    """
    Custom deployer
    """

    @staticmethod
    def _collect_requirements(
        stack: "Stack",
        pipeline_node: pipeline_pb2.PipelineNode,
    ) -> List[str]:
        """Collects all requirements necessary to create custom deployer.

        Args:
            stack: Stack on which the step is being executed.
            pipeline_node: Pipeline node info for a step.

        Returns:
            Alphabetically sorted list of pip requirements.
        """
        requirements = stack.requirements()

        # Add pipeline requirements from the corresponding node context
        for context in pipeline_node.contexts.contexts:
            if context.type.name == "pipeline_requirements":
                pipeline_requirements = context.properties[
                    "pipeline_requirements"
                ].field_value.string_value.split(" ")
                requirements.update(pipeline_requirements)
                break

        # TODO [ENG-696]: Find a nice way to set this if the running version of
        #  ZenML is not an official release (e.g. on a development branch)
        # Add the current ZenML version as a requirement
        requirements.add(f"zenml=={zenml.__version__}")

        return sorted(requirements)

    def _build_and_push_docker_image(
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
        image_name = f"{registry_uri}/seldon-custom-model:{pipeline_name}"

        docker_utils.build_docker_image(
            build_context_path=get_source_root_path(),
            image_name=image_name,
            entrypoint=" ".join(entrypoint_command),
            requirements=set(requirements),
            base_image=self.base_image,
        )
        docker_utils.push_docker_image(image_name)
        return docker_utils.get_image_digest(image_name) or image_name
