# Original License:
# Copyright 2019 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# New License:
#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestrator
from zenml.pipelines import Schedule
from zenml.steps import BaseStep

if TYPE_CHECKING:
    from zenml.pipelines import BasePipeline
    from zenml.runtime_configuration import RuntimeConfiguration

logger = get_logger(__name__)


class LocalOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines locally."""

    def provision(self) -> None:
        pass

    def deprovision(self) -> None:
        pass

    def resume(self) -> None:
        pass

    def suspend(self) -> None:
        pass

    FLAVOR: ClassVar[str] = "local"

    def prepare_steps(
        self,
        pipeline: "BasePipeline",
        sorted_list_of_steps: List[BaseStep],
        runtime_configuration: "RuntimeConfiguration",
        schedule: Schedule,
    ) -> Any:
        if schedule:
            logger.warning(
                "Local Orchestrator currently does not support the"
                "use of schedules. The `schedule` will be ignored "
                "and the pipeline will be run immediately."
            )
        assert runtime_configuration.run_name, "Run name must be set"

        for step in sorted_list_of_steps:
            self.setup_and_execute_step(
                step, run_name=runtime_configuration.run_name
            )
