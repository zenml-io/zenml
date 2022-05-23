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

from typing import TYPE_CHECKING, Any, ClassVar, List

from tfx.proto.orchestration.pipeline_pb2 import Pipeline as Pb2Pipeline

from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestrator
from zenml.stack import Stack
from zenml.steps import BaseStep

if TYPE_CHECKING:
    from zenml.pipelines import BasePipeline
    from zenml.runtime_configuration import RuntimeConfiguration

logger = get_logger(__name__)


class LocalOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines locally. This orchestrator
    does not allow for concurrent execution of steps and also does not support
    running on a schedule."""

    FLAVOR: ClassVar[str] = "local"

    def prepare_or_run_pipeline(
        self,
        sorted_steps: List[BaseStep],
        pipeline: "BasePipeline",
        pb2_pipeline: Pb2Pipeline,
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> Any:
        """This method iterates through all steps and executes them sequentially."""
        if runtime_configuration.schedule:
            logger.warning(
                "Local Orchestrator currently does not support the"
                "use of schedules. The `schedule` will be ignored "
                "and the pipeline will be run immediately."
            )
        assert runtime_configuration.run_name, "Run name must be set"

        # Run each step
        for step in sorted_steps:
            self.run_step(
                step=step,
                run_name=runtime_configuration.run_name,
                pb2_pipeline=pb2_pipeline,
            )
