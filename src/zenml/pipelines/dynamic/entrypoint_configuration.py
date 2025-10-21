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
"""Abstract base class for entrypoint configurations that run a pipeline."""

from typing import Any, Dict, List
from uuid import UUID

from zenml.client import Client
from zenml.entrypoints.base_entrypoint_configuration import (
    BaseEntrypointConfiguration,
)
from zenml.integrations.registry import integration_registry
from zenml.pipelines.dynamic.runner import DynamicPipelineRunner

RUN_ID_OPTION = "run_id"


class DynamicPipelineEntrypointConfiguration(BaseEntrypointConfiguration):
    """Base class for entrypoint configurations that run an entire pipeline."""

    @classmethod
    def get_entrypoint_options(cls) -> Dict[str, bool]:
        """Gets all options required for running with this configuration.

        Returns:
            The superclass options as well as an option for the name of the
            step to run.
        """
        return super().get_entrypoint_options() | {RUN_ID_OPTION: False}

    @classmethod
    def get_entrypoint_arguments(
        cls,
        **kwargs: Any,
    ) -> List[str]:
        """Gets all arguments that the entrypoint command should be called with.

        The argument list should be something that
        `argparse.ArgumentParser.parse_args(...)` can handle (e.g.
        `["--some_option", "some_value"]` or `["--some_option=some_value"]`).
        It needs to provide values for all options returned by the
        `get_entrypoint_options()` method of this class.

        Args:
            **kwargs: Kwargs, must include the step name.

        Returns:
            The superclass arguments as well as arguments for the name of the
            step to run.
        """
        args = super().get_entrypoint_arguments(**kwargs)
        if RUN_ID_OPTION in kwargs:
            args.extend(
                [
                    f"--{RUN_ID_OPTION}",
                    str(kwargs[RUN_ID_OPTION]),
                ]
            )
        return args

    def run(self) -> None:
        """Prepares the environment and runs the configured pipeline."""
        snapshot = self.load_snapshot()

        # Activate all the integrations. This makes sure that all materializers
        # and stack component flavors are registered.
        integration_registry.activate_integrations()

        self.download_code_if_necessary(snapshot=snapshot)

        run = None
        if run_id := self.entrypoint_args.get(RUN_ID_OPTION, None):
            run = Client().get_pipeline_run(UUID(run_id))

        runner = DynamicPipelineRunner(snapshot=snapshot, run=run)
        runner.run_pipeline()
