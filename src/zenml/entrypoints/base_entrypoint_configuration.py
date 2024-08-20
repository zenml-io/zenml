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
import os
import sys
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, NoReturn, Set
from uuid import UUID

from zenml.client import Client
from zenml.code_repositories import BaseCodeRepository
from zenml.constants import (
    ENV_ZENML_REQUIRES_CODE_DOWNLOAD,
    handle_bool_env_var,
)
from zenml.logger import get_logger
from zenml.utils import (
    code_repository_utils,
    code_utils,
    source_utils,
    uuid_utils,
)

if TYPE_CHECKING:
    from zenml.models import CodeReferenceResponse, PipelineDeploymentResponse

logger = get_logger(__name__)
DEFAULT_ENTRYPOINT_COMMAND = [
    "python",
    "-m",
    "zenml.entrypoints.entrypoint",
]

ENTRYPOINT_CONFIG_SOURCE_OPTION = "entrypoint_config_source"
DEPLOYMENT_ID_OPTION = "deployment_id"


class BaseEntrypointConfiguration(ABC):
    """Abstract base class for entrypoint configurations.

    An entrypoint configuration specifies the arguments that should be passed
    to the entrypoint and what is running inside the entrypoint.

    Attributes:
        entrypoint_args: The parsed arguments passed to the entrypoint.
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
            # ID of the pipeline deployment to use in this entrypoint
            DEPLOYMENT_ID_OPTION,
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

        Raises:
            ValueError: If no valid deployment ID is passed.
        """
        deployment_id = kwargs.get(DEPLOYMENT_ID_OPTION)
        if not uuid_utils.is_valid_uuid(deployment_id):
            raise ValueError(
                f"Missing or invalid deployment ID as argument for entrypoint "
                f"configuration. Please make sure to pass a valid UUID to "
                f"`{cls.__name__}.{cls.get_entrypoint_arguments.__name__}"
                f"({DEPLOYMENT_ID_OPTION}=<UUID>)`."
            )

        arguments = [
            f"--{ENTRYPOINT_CONFIG_SOURCE_OPTION}",
            source_utils.resolve(cls).import_path,
            f"--{DEPLOYMENT_ID_OPTION}",
            str(deployment_id),
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

        class _CustomParser(argparse.ArgumentParser):
            """Argument parser subclass that suppresses some argparse logs.

            Also raises an exception instead of the `sys.exit()` call.
            """

            def error(self, message: str) -> NoReturn:
                raise ValueError(
                    f"Failed to parse entrypoint arguments: {message}"
                )

        parser = _CustomParser()

        for option_name in cls.get_entrypoint_options():
            if option_name == ENTRYPOINT_CONFIG_SOURCE_OPTION:
                # This option is already used by
                # `zenml.entrypoints.entrypoint` to read which config
                # class to use
                continue
            parser.add_argument(f"--{option_name}", required=True)

        result, _ = parser.parse_known_args(arguments)
        return vars(result)

    def load_deployment(self) -> "PipelineDeploymentResponse":
        """Loads the deployment.

        Returns:
            The deployment.
        """
        deployment_id = UUID(self.entrypoint_args[DEPLOYMENT_ID_OPTION])
        return Client().zen_store.get_deployment(deployment_id=deployment_id)

    def download_code_if_necessary(
        self, deployment: "PipelineDeploymentResponse"
    ) -> None:
        """Downloads user code if necessary.

        Args:
            deployment: The deployment for which to download the code.

        Raises:
            RuntimeError: If the current environment requires code download
                but the deployment does not have a reference to any code.
        """
        requires_code_download = handle_bool_env_var(
            ENV_ZENML_REQUIRES_CODE_DOWNLOAD
        )

        if not requires_code_download:
            return

        if code_reference := deployment.code_reference:
            self.download_code_from_code_repository(
                code_reference=code_reference
            )
        elif code_path := deployment.code_path:
            code_utils.download_code_from_artifact_store(code_path=code_path)
        else:
            raise RuntimeError(
                "Code download required but no code reference or path provided."
            )

        logger.info("Code download finished.")

    def download_code_from_code_repository(
        self, code_reference: "CodeReferenceResponse"
    ) -> None:
        """Download code from a code repository.

        Args:
            code_reference: The reference to the code.
        """
        logger.info(
            "Downloading code from code repository `%s` (commit `%s`).",
            code_reference.code_repository.name,
            code_reference.commit,
        )

        model = Client().get_code_repository(code_reference.code_repository.id)
        repo = BaseCodeRepository.from_model(model)
        code_repo_root = os.path.abspath("code")
        download_dir = os.path.join(
            code_repo_root, code_reference.subdirectory
        )
        os.makedirs(download_dir)
        repo.download_files(
            commit=code_reference.commit,
            directory=download_dir,
            repo_sub_directory=code_reference.subdirectory,
        )
        source_utils.set_custom_source_root(download_dir)
        code_repository_utils.set_custom_local_repository(
            root=code_repo_root, commit=code_reference.commit, repo=repo
        )

        sys.path.insert(0, download_dir)
        os.chdir(download_dir)

    @abstractmethod
    def run(self) -> None:
        """Runs the entrypoint configuration."""
