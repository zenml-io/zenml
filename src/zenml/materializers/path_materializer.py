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
"""Implementation of the materializer for Path objects."""

import os
import shutil
import tarfile
from pathlib import Path
from typing import Any, ClassVar, Tuple, Type

from zenml.constants import (
    ENV_ZENML_DISABLE_PATH_MATERIALIZER,
    handle_bool_env_var,
)
from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils.io_utils import is_path_within_directory


class PathMaterializer(BaseMaterializer):
    """Materializer for Path objects.

    This materializer handles `pathlib.Path` objects by storing their contents
    in a compressed tar archive within the artifact store if it's a directory,
    or directly copying the file if it's a single file.
    """

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (Path,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA
    ARCHIVE_NAME: ClassVar[str] = "data.tar.gz"
    FILE_NAME: ClassVar[str] = "file_data"

    # Skip registration if the environment variable is set
    SKIP_REGISTRATION: ClassVar[bool] = handle_bool_env_var(
        ENV_ZENML_DISABLE_PATH_MATERIALIZER, default=False
    )

    def load(self, data_type: Type[Any]) -> Any:
        """Copy the artifact files to a local temp directory or file.

        Args:
            data_type: Unused.

        Returns:
            Path to the local directory or file that contains the artifact.

        Raises:
            FileNotFoundError: If the artifact is not found in the artifact store.
        """
        # Create a temporary directory that will persist until step execution ends
        with self.get_temporary_directory(delete_at_exit=False) as directory:
            # Check if we're loading a file or directory by looking for the archive
            archive_path_remote = os.path.join(self.uri, self.ARCHIVE_NAME)
            file_path_remote = os.path.join(self.uri, self.FILE_NAME)

            if fileio.exists(archive_path_remote):
                # This is a directory artifact
                archive_path_local = os.path.join(directory, self.ARCHIVE_NAME)
                fileio.copy(archive_path_remote, archive_path_local)

                # Extract the archive to the temporary directory
                with tarfile.open(archive_path_local, "r:gz") as tar:
                    # Validate archive members to prevent path traversal attacks
                    # Filter members to only those with safe paths
                    safe_members = []
                    for member in tar.getmembers():
                        if is_path_within_directory(member.name, directory):
                            safe_members.append(member)

                    # Extract only safe members
                    tar.extractall(path=directory, members=safe_members)  # nosec B202 - members are filtered through is_path_within_directory

                # Clean up the archive file
                os.remove(archive_path_local)
                return Path(directory)
            elif fileio.exists(file_path_remote):
                # This is a single file artifact
                file_path_local = os.path.join(
                    directory, os.path.basename(file_path_remote)
                )
                fileio.copy(file_path_remote, file_path_local)
                return Path(file_path_local)
            else:
                raise FileNotFoundError(
                    f"Could not find artifact at {archive_path_remote} or {file_path_remote}"
                )

    def save(self, data: Any) -> None:
        """Store the directory or file in the artifact store.

        Args:
            data: Path to a local directory or file to store. Must be a Path object.

        Raises:
            TypeError: If data is not a Path object.
        """
        if not isinstance(data, Path):
            raise TypeError(
                f"Expected a Path object, got {type(data).__name__}"
            )

        if data.is_dir():
            # Handle directory artifact
            with self.get_temporary_directory(
                delete_at_exit=True
            ) as directory:
                archive_base = os.path.join(directory, "data")

                # Create tar.gz archive - automatically uses relative paths
                shutil.make_archive(
                    base_name=archive_base, format="gztar", root_dir=str(data)
                )

                # Copy the archive to the artifact store
                fileio.copy(
                    f"{archive_base}.tar.gz",
                    os.path.join(self.uri, self.ARCHIVE_NAME),
                )
        else:
            # Handle single file artifact
            file_path_remote = os.path.join(self.uri, self.FILE_NAME)
            fileio.copy(str(data), file_path_remote)
