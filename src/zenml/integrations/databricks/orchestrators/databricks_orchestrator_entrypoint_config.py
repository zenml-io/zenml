#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Entrypoint configuration for ZenML Databricks pipeline steps."""

import os
import sys
from typing import Any, List, Set

import pkg_resources

from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)
from zenml.utils import source_utils

WHEEL_PACKAGE_OPTION = "wheel_package"
DATABRICKS_JOB_ID_OPTION = "databricks_job_id"
ENV_ZENML_DATABRICKS_ORCHESTRATOR_RUN_ID = (
    "ZENML_DATABRICKS_ORCHESTRATOR_RUN_ID"
)


class DatabricksEntrypointConfiguration(StepEntrypointConfiguration):
    """Entrypoint configuration for ZenML Databricks pipeline steps.

    The only purpose of this entrypoint configuration is to reconstruct the
    environment variables that exceed the maximum length of 256 characters
    allowed for Databricks Processor steps from their individual components.
    """

    def __init__(self, arguments: List[str]):
        """Initializes the entrypoint configuration.

        Args:
            arguments: Command line arguments to configure this object.
        """
        source_utils.set_custom_source_root(source_root=os.getcwd())
        super().__init__(arguments)

    @classmethod
    def get_entrypoint_options(cls) -> Set[str]:
        """Gets all options required for running with this configuration.

        Returns:
            The superclass options as well as an option for the wheel package.
        """
        return (
            super().get_entrypoint_options()
            | {WHEEL_PACKAGE_OPTION}
            | {DATABRICKS_JOB_ID_OPTION}
        )

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
            The superclass arguments as well as arguments for the wheel package.
        """
        return super().get_entrypoint_arguments(**kwargs) + [
            f"--{WHEEL_PACKAGE_OPTION}",
            kwargs[WHEEL_PACKAGE_OPTION],
            f"--{DATABRICKS_JOB_ID_OPTION}",
            kwargs[DATABRICKS_JOB_ID_OPTION],
        ]

    def run(self) -> None:
        """Runs the step."""
        # Get the wheel package and add it to the sys path
        wheel_package = self.entrypoint_args[WHEEL_PACKAGE_OPTION]
        distribution = pkg_resources.get_distribution(wheel_package)
        project_root = os.path.join(distribution.location, wheel_package)
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
            sys.path.insert(-1, project_root)

        # Get the job id and add it to the environment
        databricks_job_id = self.entrypoint_args[DATABRICKS_JOB_ID_OPTION]
        os.environ[ENV_ZENML_DATABRICKS_ORCHESTRATOR_RUN_ID] = (
            databricks_job_id
        )

        # Run the step
        super().run()
