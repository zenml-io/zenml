#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Entrypoint configuration to run a dynamic pipeline."""

from typing import Any, Dict, List
from uuid import UUID

from zenml.client import Client
from zenml.entrypoints.base_entrypoint_configuration import (
    BaseEntrypointConfiguration,
)
from zenml.execution.pipeline.dynamic.runner import DynamicPipelineRunner
from zenml.integrations.registry import integration_registry

RUN_ID_OPTION = "run_id"


class DynamicPipelineEntrypointConfiguration(BaseEntrypointConfiguration):
    """Entrypoint configuration to run a dynamic pipeline."""

    @classmethod
    def get_entrypoint_options(cls) -> Dict[str, bool]:
        """Gets all options required for running with this configuration.

        Returns:
            All options required for running with this configuration.
        """
        return super().get_entrypoint_options() | {RUN_ID_OPTION: False}

    @classmethod
    def get_entrypoint_arguments(
        cls,
        **kwargs: Any,
    ) -> List[str]:
        """Gets all arguments that the entrypoint command should be called with.

        Args:
            **kwargs: Keyword arguments.

        Returns:
            All arguments that the entrypoint command should be called with.
        """
        args = super().get_entrypoint_arguments(**kwargs)
        if run_id := kwargs.get(RUN_ID_OPTION, None):
            args.extend([f"--{RUN_ID_OPTION}", str(run_id)])
        return args

    def run(self) -> None:
        """Prepares the environment and runs the configured dynamic pipeline."""
        snapshot = self.snapshot

        # Activate all the integrations. This makes sure that all materializers
        # and stack component flavors are registered.
        integration_registry.activate_integrations()

        self.download_code_if_necessary()

        run = None
        if run_id := self.entrypoint_args.get(RUN_ID_OPTION, None):
            run = Client().get_pipeline_run(UUID(run_id))

        runner = DynamicPipelineRunner(snapshot=snapshot, run=run)
        runner.run_pipeline()
