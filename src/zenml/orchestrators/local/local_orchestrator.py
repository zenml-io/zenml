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
"""Implementation of the ZenML local orchestrator."""

import time
from typing import TYPE_CHECKING, Any, Dict, Optional, Type
from uuid import uuid4

from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestrator
from zenml.orchestrators.base_orchestrator import (
    BaseOrchestratorConfig,
    BaseOrchestratorFlavor,
)
from zenml.stack import Stack
from zenml.utils import string_utils

if TYPE_CHECKING:
    from zenml.models import PipelineDeploymentResponse

logger = get_logger(__name__)


class LocalOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines locally.

    This orchestrator does not allow for concurrent execution of steps and also
    does not support running on a schedule.
    """

    _orchestrator_run_id: Optional[str] = None

    def prepare_or_run_pipeline(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        environment: Dict[str, str],
    ) -> Any:
        """Iterates through all steps and executes them sequentially.

        Args:
            deployment: The pipeline deployment to prepare or run.
            stack: The stack on which the pipeline is deployed.
            environment: Environment variables to set in the orchestration
                environment.

        Returns:
            The pipeline run object.
        """
        if deployment.schedule:
            logger.warning(
                "Local Orchestrator currently does not support the "
                "use of schedules. The `schedule` will be ignored "
                "and the pipeline will be run immediately."
            )

        self._orchestrator_run_id = str(uuid4())
        start_time = time.time()

        # Run each step
        for step_name, step in deployment.step_configurations.items():
            if self.requires_resources_in_orchestration_environment(step):
                logger.warning(
                    "Specifying step resources is not supported for the local "
                    "orchestrator, ignoring resource configuration for "
                    "step %s.",
                    step_name,
                )

            self.run_step(
                step=step,
            )

        run_duration = time.time() - start_time
        logger.info(
            "Pipeline run has finished in `%s`.",
            string_utils.get_human_readable_time(run_duration),
        )
        self._orchestrator_run_id = None

    def get_orchestrator_run_id(self) -> str:
        """Returns the active orchestrator run id.

        Raises:
            RuntimeError: If no run id exists. This happens when this method
                gets called while the orchestrator is not running a pipeline.

        Returns:
            The orchestrator run id.
        """
        if not self._orchestrator_run_id:
            raise RuntimeError("No run id set.")

        return self._orchestrator_run_id


class LocalOrchestratorConfig(BaseOrchestratorConfig):
    """Local orchestrator config."""

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Returns:
            True if this config is for a local component, False otherwise.
        """
        return True

    @property
    def is_synchronous(self) -> bool:
        """Whether the orchestrator runs synchronous or not.

        Returns:
            Whether the orchestrator runs synchronous or not.
        """
        return True


class LocalOrchestratorFlavor(BaseOrchestratorFlavor):
    """Class for the `LocalOrchestratorFlavor`."""

    @property
    def name(self) -> str:
        """The flavor name.

        Returns:
            The flavor name.
        """
        return "local"

    @property
    def docs_url(self) -> Optional[str]:
        """A URL to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A URL to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A URL to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/local.png"

    @property
    def config_class(self) -> Type[BaseOrchestratorConfig]:
        """Config class for the base orchestrator flavor.

        Returns:
            The config class.
        """
        return LocalOrchestratorConfig

    @property
    def implementation_class(self) -> Type[LocalOrchestrator]:
        """Implementation class for this flavor.

        Returns:
            The implementation class for this flavor.
        """
        return LocalOrchestrator
