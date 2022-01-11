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

from typing import TYPE_CHECKING, Any

from pydantic import PrivateAttr

from zenml.orchestrators import BaseOrchestrator
from zenml.orchestrators.local.local_dag_runner import LocalDagRunner
from zenml.orchestrators.utils import create_tfx_pipeline

if TYPE_CHECKING:
    from zenml.pipelines.base_pipeline import BasePipeline


class LocalOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines locally."""

    _is_running: bool = PrivateAttr(default=False)

    @property
    def is_running(self) -> bool:
        """Returns whether the orchestrator is currently running."""
        return self._is_running

    def run(
        self,
        zenml_pipeline: "BasePipeline",
        run_name: str,
        **pipeline_args: Any
    ) -> None:
        """Runs a pipeline locally.

        Args:
            zenml_pipeline: The pipeline to run.
            run_name: Name of the pipeline run.
            **pipeline_args: Unused kwargs to conform with base signature.
        """
        self._is_running = True
        runner = LocalDagRunner()
        tfx_pipeline = create_tfx_pipeline(zenml_pipeline)
        runner.run(tfx_pipeline, run_name)
        self._is_running = False
