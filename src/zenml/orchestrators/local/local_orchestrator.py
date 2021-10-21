# New Licence:
#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from typing import TYPE_CHECKING, Any

import tfx.orchestration.pipeline as tfx_pipeline

from zenml.core.component_factory import orchestrator_store_factory
from zenml.enums import OrchestratorTypes
from zenml.orchestrators.base_orchestrator import BaseOrchestrator
from zenml.orchestrators.local.local_dag_runner import LocalDagRunner
from zenml.steps.base_step import BaseStep

if TYPE_CHECKING:
    from zenml.pipelines.base_pipeline import BasePipeline


@orchestrator_store_factory.register(OrchestratorTypes.local)
class LocalOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines locally."""

    def run(self, zenml_pipeline: "BasePipeline", **pipeline_args: Any) -> None:
        """Runs a pipeline locally.

        Args:
            zenml_pipeline: The pipeline to run.
            **pipeline_args: Unused kwargs to conform with base signature.
        """
        runner = LocalDagRunner()

        # Establish the connections between the components
        for s in zenml_pipeline.steps.values():
            if not issubclass(type(s), BaseStep):
                raise TypeError(
                    f"When you are designing a pipeline, you can only pass in "
                    f"@step like annotated objects. You passed in "
                    f"`{s}` which is of type `{type(s)}`"
                )

        zenml_pipeline.connect(**zenml_pipeline.steps)

        # Create the final step list and the corresponding pipeline
        steps = [s.component for s in zenml_pipeline.steps.values()]

        artifact_store = zenml_pipeline.stack.artifact_store
        metadata_store = zenml_pipeline.stack.metadata_store

        created_pipeline = tfx_pipeline.Pipeline(
            pipeline_name=zenml_pipeline.name,
            components=steps,  # type: ignore[arg-type]
            pipeline_root=artifact_store.path,
            metadata_connection_config=metadata_store.get_tfx_metadata_config(),
            enable_cache=zenml_pipeline.enable_cache,
        )
        return runner.run(created_pipeline)
