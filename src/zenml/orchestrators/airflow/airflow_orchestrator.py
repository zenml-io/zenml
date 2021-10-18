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

import datetime
from typing import TYPE_CHECKING

from tfx.dsl.components.common.importer import Importer
from tfx.orchestration import pipeline as tfx_pipeline

from zenml.core.component_factory import orchestrator_store_factory
from zenml.enums import OrchestratorTypes
from zenml.orchestrators.airflow.airflow_dag_runner import (
    AirflowDagRunner,
    AirflowPipelineConfig,
)
from zenml.orchestrators.base_orchestrator import BaseOrchestrator

if TYPE_CHECKING:
    from zenml.pipelines.base_pipeline import BasePipeline


@orchestrator_store_factory.register(OrchestratorTypes.airflow)
class AirflowOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines using Airflow."""

    def run(self, zenml_pipeline: "BasePipeline", **kwargs):
        """Prepares the pipeline so it can be run in Airflow.

        Args:
            zenml_pipeline: The pipeline to run.
            **kwargs: Unused argument to conform with base class signature.
        """
        # TODO: [LOW] remove or modify the configuration here
        _airflow_config = {
            "schedule_interval": None,
            "start_date": datetime.datetime(2019, 1, 1),
        }

        runner = AirflowDagRunner(AirflowPipelineConfig(_airflow_config))

        # Resolve the importers for external artifact inputs
        importers = {}
        for name, artifact in zenml_pipeline.inputs.items():
            importers[name] = Importer(
                source_uri=artifact.uri, artifact_type=artifact.type
            ).with_id(name)

        import_artifacts = {
            n: i.outputs["result"] for n, i in importers.items()
        }

        # Establish the connections between the components
        zenml_pipeline.connect(**import_artifacts, **zenml_pipeline.steps)

        # Create the final step list and the corresponding pipeline
        steps = list(importers.values()) + [
            s.component for s in zenml_pipeline.steps.values()
        ]

        artifact_store = zenml_pipeline.stack.artifact_store
        metadata_store = zenml_pipeline.stack.metadata_store

        created_pipeline = tfx_pipeline.Pipeline(
            pipeline_name=zenml_pipeline.name,
            components=steps,
            pipeline_root=artifact_store.path,
            metadata_connection_config=metadata_store.get_tfx_metadata_config(),
            enable_cache=True,
        )

        return runner.run(created_pipeline)
