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

import json
from typing import TYPE_CHECKING, Any, ClassVar, List, Dict

from tfx.dsl.compiler.compiler import Compiler
from tfx.dsl.compiler.constants import PIPELINE_RUN_ID_PARAMETER_NAME
from tfx.dsl.components.base import base_component
from tfx.orchestration import metadata
from tfx.orchestration.local import runner_utils
from tfx.orchestration.pipeline import Pipeline as TfxPipeline
from tfx.orchestration.portable import launcher, runtime_parameter_utils
from tfx.proto.orchestration import executable_spec_pb2
from tfx.proto.orchestration.pipeline_pb2 import Pipeline as Pb2Pipeline
from tfx.proto.orchestration.pipeline_pb2 import PipelineNode

from zenml.enums import MetadataContextTypes
from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestrator, context_utils
from zenml.orchestrators.utils import (
    create_tfx_pipeline,
    execute_step,
    get_step_for_node,
)
from zenml.repository import Repository
from zenml.steps import BaseStep

if TYPE_CHECKING:
    from zenml.pipelines.base_pipeline import BasePipeline
    from zenml.runtime_configuration import RuntimeConfiguration
    from zenml.stack import Stack


logger = get_logger(__name__)


class LocalOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines locally."""

    # Class Configuration
    FLAVOR: ClassVar[str] = "local"

    def something_something_step(self,
                                 sorted_list_of_steps: List[Dict[str, BaseStep]]
                                 ) -> None:

        for step in sorted_list_of_steps:
            self.setup_and_execute_step(step)
