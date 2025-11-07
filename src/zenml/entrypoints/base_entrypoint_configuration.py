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
from typing import TYPE_CHECKING, Any, Dict, List, NoReturn, Optional
from uuid import UUID

from zenml.client import Client
from zenml.code_repositories import BaseCodeRepository
from zenml.enums import StackComponentType
from zenml.exceptions import CustomFlavorImportError
from zenml.logger import get_logger
from zenml.utils import (
    code_repository_utils,
    code_utils,
    source_utils,
    uuid_utils,
)

if TYPE_CHECKING:
    from zenml.artifact_stores import BaseArtifactStore
    from zenml.config import DockerSettings
    from zenml.models import CodeReferenceResponse, PipelineSnapshotResponse

logger = get_logger(__name__)
DEFAULT_ENTRYPOINT_COMMAND = [
    "python",
    "-m",
    "zenml.entrypoints.entrypoint",
]

ENTRYPOINT_CONFIG_SOURCE_OPTION = "entrypoint_config_source"
SNAPSHOT_ID_OPTION = "snapshot_id"


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
        self._snapshot: Optional["PipelineSnapshotResponse"] = None

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
    def get_entrypoint_options(cls) -> Dict[str, bool]:
        """Gets all options required for running with this configuration.

        Returns:
            A dictionary of options and whether they are required.
        """
        return {
            # Importable source pointing to the entrypoint configuration class
            # that should be used inside the entrypoint.
            ENTRYPOINT_CONFIG_SOURCE_OPTION: True,
            # ID of the pipeline snapshot to use in this entrypoint
            SNAPSHOT_ID_OPTION: True,
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
            ValueError: If no valid snapshot ID is passed.
        """
        arguments = [
            f"--{ENTRYPOINT_CONFIG_SOURCE_OPTION}",
            source_utils.resolve(cls).import_path,
        ]

        if SNAPSHOT_ID_OPTION in cls.get_entrypoint_options():
            snapshot_id = kwargs.get(SNAPSHOT_ID_OPTION)
            if not uuid_utils.is_valid_uuid(snapshot_id):
                raise ValueError(
                    f"Missing or invalid snapshot ID as argument for entrypoint "
                    f"configuration. Please make sure to pass a valid UUID to "
                    f"`{cls.__name__}.{cls.get_entrypoint_arguments.__name__}"
                    f"({SNAPSHOT_ID_OPTION}=<UUID>)`."
                )

            arguments.extend(
                [
                    f"--{SNAPSHOT_ID_OPTION}",
                    str(snapshot_id),
                ]
            )

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

        for option_name, required in cls.get_entrypoint_options().items():
            if option_name == ENTRYPOINT_CONFIG_SOURCE_OPTION:
                # This option is already used by
                # `zenml.entrypoints.entrypoint` to read which config
                # class to use
                continue
            parser.add_argument(f"--{option_name}", required=required)

        result, _ = parser.parse_known_args(arguments)
        return vars(result)

    @property
    def snapshot(self) -> "PipelineSnapshotResponse":
        """The snapshot configured for this entrypoint configuration.

        Returns:
            The snapshot.
        """
        if self._snapshot is None:
            self._snapshot = self._load_snapshot()
        return self._snapshot

    @property
    def docker_settings(self) -> "DockerSettings":
        """The Docker settings configured for this entrypoint configuration.

        Returns:
            The Docker settings.
        """
        return self.snapshot.pipeline_configuration.docker_settings

    @property
    def should_download_code(self) -> bool:
        """Whether code should be downloaded.

        Returns:
            Whether code should be downloaded.
        """
        if (
            self.snapshot.code_reference
            and self.docker_settings.allow_download_from_code_repository
        ):
            return True

        if (
            self.snapshot.code_path
            and self.docker_settings.allow_download_from_artifact_store
        ):
            return True

        return False

    def _load_snapshot(self) -> "PipelineSnapshotResponse":
        """Loads the snapshot.

        Returns:
            The snapshot.
        """
        snapshot_id = UUID(self.entrypoint_args[SNAPSHOT_ID_OPTION])
        return Client().zen_store.get_snapshot(snapshot_id=snapshot_id)

    def download_code_if_necessary(self) -> None:
        """Downloads user code if necessary.

        Raises:
            CustomFlavorImportError: If the artifact store flavor can't be
                imported.
            RuntimeError: If the current environment requires code download
                but the snapshot does not have a reference to any code.
        """
        if not self.should_download_code:
            return

        if code_path := self.snapshot.code_path:
            # Load the artifact store not from the active stack but separately.
            # This is required in case the stack has custom flavor components
            # (other than the artifact store) for which the flavor
            # implementations will only be available once the download finishes.
            try:
                artifact_store = self._load_active_artifact_store()
            except CustomFlavorImportError as e:
                raise CustomFlavorImportError(
                    "Failed to import custom artifact store flavor. The "
                    "artifact store flavor is needed to download your code, "
                    "but it looks like it might be part of the files "
                    "that we're trying to download. If this is the case, you "
                    "should disable downloading code from the artifact store "
                    "using `DockerSettings(allow_download_from_artifact_store=False)` "
                    "or make sure the artifact flavor files are included in "
                    "Docker image by using a custom parent image or installing "
                    "them as part of a pip dependency."
                ) from e
            code_utils.download_code_from_artifact_store(
                code_path=code_path, artifact_store=artifact_store
            )
        elif code_reference := self.snapshot.code_reference:
            # TODO: This might fail if the code repository had unpushed changes
            # at the time the pipeline run was started.
            self.download_code_from_code_repository(
                code_reference=code_reference
            )
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
        os.makedirs(download_dir, exist_ok=True)
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

    def _load_active_artifact_store(self) -> "BaseArtifactStore":
        """Load the active artifact store.

        Returns:
            The active artifact store.
        """
        from zenml.artifact_stores import BaseArtifactStore

        artifact_store_model = Client().active_stack_model.components[
            StackComponentType.ARTIFACT_STORE
        ][0]
        artifact_store = BaseArtifactStore.from_model(artifact_store_model)
        assert isinstance(artifact_store, BaseArtifactStore)

        return artifact_store

    @abstractmethod
    def run(self) -> None:
        """Runs the entrypoint configuration."""
