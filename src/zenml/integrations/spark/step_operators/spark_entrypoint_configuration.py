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
"""Spark step operator entrypoint configuration."""
from zenml.step_operators.step_operator_entrypoint_configuration import (
    StepOperatorEntrypointConfiguration,
)
from zenml.utils import source_utils
from zenml.utils.pipeline_docker_image_builder import DOCKER_IMAGE_WORKDIR


class SparkEntrypointConfiguration(StepOperatorEntrypointConfiguration):
    """Entrypoint configuration for the Spark step operator."""

    def run(self) -> None:
        """Runs the entrypoint configuration.

        This prepends the directory containing the source files to the python
        path so that spark can find them.
        """
        with source_utils.prepend_python_path([DOCKER_IMAGE_WORKDIR]):
            super().run()
