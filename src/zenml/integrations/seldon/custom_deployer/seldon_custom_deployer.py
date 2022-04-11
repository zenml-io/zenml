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

if TYPE_CHECKING:
    from zenml.stack import Stack


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
