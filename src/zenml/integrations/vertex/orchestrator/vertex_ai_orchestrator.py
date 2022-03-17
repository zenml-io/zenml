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
from google.cloud import aiplatform
from google.cloud.aiplatform import pipeline_jobs
from typing import TYPE_CHECKING, Any, Optional
from zenml.stack import Stack, StackValidator
from zenml.utils import docker_utils
from zenml.enums import StackComponentType, StepOperatorFlavor
from zenml.repository import Repository
from zenml.stack.stack_component_class_registry import (
    register_stack_component_class,
)
from zenml.step_operators import BaseStepOperator

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

from zenml.enums import MetadataContextTypes, OrchestratorFlavor
from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestrator, context_utils
from zenml.orchestrators.utils import (
    create_tfx_pipeline,
    execute_step,
    get_step_for_node,
)
from zenml.repository import Repository
from zenml.integrations.kubeflow.orchestrators import KubeflowOrchestrator

if TYPE_CHECKING:
    from zenml.pipelines.base_pipeline import BasePipeline
    from zenml.runtime_configuration import RuntimeConfiguration
    from zenml.stack import Stack


logger = get_logger(__name__)

@register_stack_component_class(
    component_type=StackComponentType.ORCHESTRATOR,
    component_flavor=OrchestratorFlavor.VERTEX,
)
class VertexOrchestrator(KubeflowOrchestrator):
    """Orchestrator responsible for running pipelines on Vertex AI."""

    supports_local_execution = False
    supports_remote_execution = True

    @property
    def flavor(self) -> OrchestratorFlavor:
        """The orchestrator flavor."""
        return OrchestratorFlavor.VERTEX

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates that the stack contains a container registry."""

        def _ensure_kubeflow_orchestrator(stack: Stack) -> bool:
            return stack.orchestrator.flavor == OrchestratorFlavor.KUBEFLOW

        return StackValidator(
            required_components={StackComponentType.CONTAINER_REGISTRY},
            custom_validation_function=_ensure_kubeflow_orchestrator,
        )

    def run_pipeline(
        self,
        pipeline: "BasePipeline",
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> Any:
        """Runs a pipeline on Vertex AI using the Kubeflow orchestrator."""

        super().run_pipeline(pipeline, stack, runtime_configuration)

        # docs_infra: no_execute

        import logging
        logging.getLogger().setLevel(logging.INFO)

        aiplatform.init(project=GOOGLE_CLOUD_PROJECT,
                        location=GOOGLE_CLOUD_REGION)

        job = pipeline_jobs.PipelineJob(template_path=PIPELINE_DEFINITION_FILE,
                                        display_name=PIPELINE_NAME)
        job.submit()
