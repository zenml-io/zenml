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
"""Abstract base class for entrypoint configurations."""

import argparse
from abc import ABC, abstractmethod
from typing import Any, Dict, List, NoReturn, Set

from zenml.config.pipeline_deployment import PipelineDeployment
from zenml.constants import DOCKER_IMAGE_DEPLOYMENT_CONFIG_FILE
from zenml.utils import source_utils, yaml_utils

DEFAULT_ENTRYPOINT_COMMAND = [
    "python",
    "-m",
    "zenml.entrypoints.entrypoint",
]

ENTRYPOINT_CONFIG_SOURCE_OPTION = "entrypoint_config_source"


class BaseEntrypointConfiguration(ABC):
    """Abstract base class for entrypoint configurations.

    An entrypoint configuration specifies the arguments that should be passed
    to the entrypoint and what is running inside the entrypoint.

    Attributes:
        entrypoint_args: The parsed arguments passed to the entrypoint.
    ```
    """

    def __init__(self, arguments: List[str]):
        """Initializes the entrypoint configuration.

        Args:
            arguments: Command line arguments to configure this object.
        """
        self.entrypoint_args = self._parse_arguments(arguments)

    @classmethod
    def get_entrypoint_command(cls) -> List[str]:
        """Returns a command that runs the entrypoint module.

        This entrypoint module is responsible for running the entrypoint
        configuration when called. Defaults to running the
        `zenml.entrypoints.entrypoint` module.

        **Note**: This command won't work on its own but needs to be called with
            the arguments returned by the `get_entrypoint_arguments(...)`
            method of this class.

        Returns:
            A list of strings with the command.
        """
        return DEFAULT_ENTRYPOINT_COMMAND

    @classmethod
    def get_entrypoint_options(cls) -> Set[str]:
        """Gets all options required for running with this configuration.

        Returns:
            A set of strings with all required options.
        """
        return {
            # Importable source pointing to the entrypoint configuration class
            # that should be used inside the entrypoint.
            ENTRYPOINT_CONFIG_SOURCE_OPTION,
        }

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
            **kwargs: Keyword args.

        Returns:
            A list of strings with the arguments.
        """
        arguments = [
            f"--{ENTRYPOINT_CONFIG_SOURCE_OPTION}",
            source_utils.resolve_class(cls),
        ]

        return arguments

    @classmethod
    def _parse_arguments(cls, arguments: List[str]) -> Dict[str, Any]:
        """Parses command line arguments.

        This method will create an `argparse.ArgumentParser` and add required
        arguments for all the options specified in the
        `get_entrypoint_options()` method of this class.

        Args:
            arguments: Arguments to parse. The format should be something that
                `argparse.ArgumentParser.parse_args(...)` can handle (e.g.
                `["--some_option", "some_value"]` or
                `["--some_option=some_value"]`).

        Returns:
            Dictionary of the parsed arguments.

        # noqa: DAR402
        Raises:
            ValueError: If the arguments are not valid.
        """
        # Argument parser subclass that suppresses some argparse logs and
        # raises an exception instead of the `sys.exit()` call
        class _CustomParser(argparse.ArgumentParser):
            def error(self, message: str) -> NoReturn:
                raise ValueError(
                    f"Failed to parse entrypoint arguments: {message}"
                )

        parser = _CustomParser()

        for option_name in cls.get_entrypoint_options():
            if option_name == ENTRYPOINT_CONFIG_SOURCE_OPTION:
                # This option is already used by
                # `zenml.entrypoints.step_entrypoint` to read which config
                # class to use
                continue
            parser.add_argument(f"--{option_name}", required=True)

        result, _ = parser.parse_known_args(arguments)
        return vars(result)

    def load_deployment_config(self) -> "PipelineDeployment":
        """Loads the deployment config.

        Returns:
            The deployment config.
        """
        config_dict = yaml_utils.read_yaml(DOCKER_IMAGE_DEPLOYMENT_CONFIG_FILE)
        return PipelineDeployment.parse_obj(config_dict)

    @abstractmethod
    def run(self) -> None:
        """Runs the entrypoint configuration."""
