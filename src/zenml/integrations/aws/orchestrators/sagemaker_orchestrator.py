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
"""Implementation of the SageMaker orchestrator."""

from typing import TYPE_CHECKING, Any, cast

import sagemaker

from zenml.integrations.aws.flavors.sagemaker_orchestrator_flavor import (
    SagemakerOrchestratorConfig,
)
from zenml.orchestrators.base_orchestrator import BaseOrchestrator

if TYPE_CHECKING:
    from zenml.config.pipeline_deployment import PipelineDeployment
    from zenml.stack import Stack


class SageMakerOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines on Sagemaker."""

    @property
    def config(self) -> SagemakerOrchestratorConfig:
        """Returns the `SagemakerOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(SagemakerOrchestratorConfig, self._config)

    def prepare_or_run_pipeline(
        self, deployment: "PipelineDeployment", stack: "Stack"
    ) -> Any:
        """Prepares or runs a pipeline on Sagemaker.

        Args:
            deployment: The deployment to prepare or run.
            stack: The stack to run on.

        Returns:
            The result of the pipeline run.
        """
        session = sagemaker.Session(default_bucket=self.config.bucket)
        for step in deployment.steps.values():
            self.run_step(
                step=step,
            )
