#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Entrypoint configuration for Databricks step operator execution."""

from typing import Any, Dict, List

from zenml.integrations.databricks.utils.databricks_utils import (
    ENV_ZENML_DATABRICKS_WHEEL_PACKAGE,
    add_wheel_package_to_sys_path,
)
from zenml.step_operators.step_operator_entrypoint_configuration import (
    StepOperatorEntrypointConfiguration,
)

WHEEL_PACKAGE_OPTION = "wheel_package"


class DatabricksStepOperatorEntrypointConfiguration(
    StepOperatorEntrypointConfiguration
):
    """Entrypoint configuration for Databricks step operator steps."""

    @classmethod
    def get_entrypoint_command(cls) -> List[str]:
        """Returns the command used by Databricks Python wheel tasks.

        Returns:
            Databricks wheel task entrypoint command.
        """
        return ["entrypoint.main"]

    @classmethod
    def get_entrypoint_options(cls) -> Dict[str, bool]:
        """Gets all options required for running with this configuration.

        Returns:
            The superclass options plus the wheel package option.
        """
        return super().get_entrypoint_options() | {
            WHEEL_PACKAGE_OPTION: False,
        }

    @classmethod
    def get_entrypoint_arguments(
        cls,
        **kwargs: Any,
    ) -> List[str]:
        """Gets the arguments for the Databricks step operator entrypoint.

        Args:
            **kwargs: Keyword arguments, must include the wheel package.

        Returns:
            The entrypoint arguments.
        """
        arguments = super().get_entrypoint_arguments(**kwargs)
        if WHEEL_PACKAGE_OPTION in kwargs:
            arguments.extend(
                [
                    f"--{WHEEL_PACKAGE_OPTION}",
                    kwargs[WHEEL_PACKAGE_OPTION],
                ]
            )
        return arguments

    def run(self) -> None:
        """Runs the Databricks step operator step."""
        wheel_package = self.entrypoint_args.get(WHEEL_PACKAGE_OPTION)
        if wheel_package:
            import os

            add_wheel_package_to_sys_path(wheel_package)
            os.environ[ENV_ZENML_DATABRICKS_WHEEL_PACKAGE] = wheel_package
        super().run()
