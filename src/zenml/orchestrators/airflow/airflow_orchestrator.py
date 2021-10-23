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
import os
from typing import TYPE_CHECKING, Any, Dict, Optional

import tfx.orchestration.pipeline as tfx_pipeline

from zenml.core.component_factory import orchestrator_store_factory
from zenml.enums import OrchestratorTypes
from zenml.orchestrators.airflow.airflow_dag_runner import (
    AirflowDagRunner,
    AirflowPipelineConfig,
)
from zenml.orchestrators.base_orchestrator import BaseOrchestrator
from zenml.utils import path_utils

if TYPE_CHECKING:
    import airflow

    from zenml.pipelines.base_pipeline import BasePipeline


@orchestrator_store_factory.register(OrchestratorTypes.airflow)
class AirflowOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines using Airflow."""

    airflow_home: str = ""
    airflow_config: Optional[Dict[str, Any]] = {}
    schedule_interval_minutes: int = 1

    def _set_env(self) -> None:
        self.airflow_home = os.getcwd()
        os.environ["AIRFLOW_HOME"] = self.airflow_home
        os.environ["AIRFLOW__CORE__DAGS_FOLDER"] = self.airflow_home
        os.environ["AIRFLOW__CORE__DAG_DISCOVERY_SAFE_MODE"] = "false"

    def bootstrap_airflow(self) -> None:
        """Starts Airflow with the standalone command."""
        self._set_env()
        from zenml.orchestrators.airflow.zenml_standalone_command import (
            ZenStandaloneCommand,
        )

        standalone = ZenStandaloneCommand()
        if not standalone.is_ready():
            standalone.run()

    def run(
        self, zenml_pipeline: "BasePipeline", **kwargs: Any
    ) -> "airflow.DAG":
        """Prepares the pipeline so it can be run in Airflow.

        Args:
            zenml_pipeline: The pipeline to run.
            **kwargs: Unused argument to conform with base class signature.
        """
        self._set_env()
        if not path_utils.file_exists(os.path.join(os.getcwd(), "airflow.cfg")):
            self.bootstrap_airflow()

        self.airflow_config = {
            "schedule_interval": datetime.timedelta(
                minutes=self.schedule_interval_minutes
            ),
            # We set this in the past and turn catchup off and then it works
            "start_date": datetime.datetime(2019, 1, 1),
        }

        runner = AirflowDagRunner(AirflowPipelineConfig(self.airflow_config))

        # Establish the connections between the components
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
