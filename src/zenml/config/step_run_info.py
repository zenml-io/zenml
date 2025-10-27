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

from zenml.config.frozen_base_model import FrozenBaseModel
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.step_configurations import StepConfiguration, StepSpec
from zenml.logger import get_logger
from zenml.models import PipelineSnapshotResponse

logger = get_logger(__name__)


class StepRunInfo(FrozenBaseModel):
    """All information necessary to run a step."""

    step_run_id: UUID
    run_id: UUID
    run_name: str
    pipeline_step_name: str

    config: StepConfiguration
    spec: StepSpec
    pipeline: PipelineConfiguration
    snapshot: PipelineSnapshotResponse

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
        if not self.snapshot.build:
            raise RuntimeError(
                f"Missing build for snapshot {self.snapshot.id}. This is "
                "probably because the build was manually deleted."
            )

        if self.snapshot.is_dynamic:
            step_key = self.config.template
            if not step_key:
                logger.warning(
                    "Unable to find config template for step %s. Falling "
                    "back to the pipeline image.",
                    self.pipeline_step_name,
                )
                step_key = None
        else:
            step_key = self.pipeline_step_name

        return self.snapshot.build.get_image(component_key=key, step=step_key)
