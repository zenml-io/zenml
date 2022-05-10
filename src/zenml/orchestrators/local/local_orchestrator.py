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

from typing import TYPE_CHECKING, ClassVar, Dict, List, Any

from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestrator
from zenml.steps import BaseStep

if TYPE_CHECKING:
    pass


logger = get_logger(__name__)


class LocalOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines locally."""

    # Class Configuration
    FLAVOR: ClassVar[str] = "local"

    def something_something_step(
        self, sorted_list_of_steps: List[BaseStep]
    ) -> Any:

        for step in sorted_list_of_steps:
            self.setup_and_execute_step(step)
