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
"""Step run info."""

from typing import Any, Callable
from uuid import UUID

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.step_configurations import StepConfiguration
from zenml.config.strict_base_model import StrictBaseModel


class StepRunInfo(StrictBaseModel):
    """All information necessary to run a step."""

    step_run_id: UUID
    run_id: UUID
    run_name: str
    pipeline_step_name: str

    config: StepConfiguration
    pipeline: PipelineConfiguration

    force_write_logs: Callable[..., Any]

    def get_image(self, key: str) -> str:
        """Gets the Docker image for the given key.

        Args:
            key: The key for which to get the image.

        Raises:
            RuntimeError: If the run does not have an associated build.

        Returns:
            The image name or digest.
        """
        from zenml.client import Client

        run = Client().get_pipeline_run(self.run_id)
        if not run.build:
            raise RuntimeError(
                f"Missing build for run {run.id}. This is probably because "
                "the build was manually deleted."
            )

        return run.build.get_image(
            component_key=key, step=self.pipeline_step_name
        )
