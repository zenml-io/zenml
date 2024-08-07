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
"""Image build context."""

import zipfile
from zenml.utils.enum_utils import StrEnum
import os
from pathlib import Path
from typing import IO, Dict, List, Optional, Set, Tuple, cast

from zenml.constants import REPOSITORY_DIRECTORY_NAME
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import io_utils, string_utils

logger = get_logger(__name__)


class ArchiveType(StrEnum):
    """Archive types supported by the ZenML build context."""

    TAR = "tar"
    TAR_GZ = "tar.gz"
    ZIP = "zip"


class BuildContext:
    """Image build context.

    This class is responsible for creating an archive of the files needed to
    build a container image.
    """

    def __init__(
        self,
        root: Optional[str] = None,
        dockerignore_file: Optional[str] = None,
    ) -> None:
        """Initializes a build context.

        Args:
            root: Optional root directory for the build context.
            dockerignore_file: Optional path to a dockerignore file. If not
                given, a file called `.dockerignore` in the build context root
                directory will be used instead if it exists.
        """
        self._root = root
        self._dockerignore_file = dockerignore_file
        self._extra_files: Dict[str, str] = {}

    @property
    def dockerignore_file(self) -> Optional[str]:
        """The dockerignore file to use.

        Returns:
            Path to the dockerignore file to use.
        """
        if self._dockerignore_file:
            return self._dockerignore_file

        if self._root:
            default_dockerignore_path = os.path.join(
                self._root, ".dockerignore"
            )
            if fileio.exists(default_dockerignore_path):
                return default_dockerignore_path

        return None

    def add_file(self, source: str, destination: str) -> None:
        """Adds a file to the build context.

        Args:
            source: The source of the file to add. This can either be a path
                or the file content.
            destination: The path inside the build context where the file
                should be added.
        """
        if fileio.exists(source):
            with fileio.open(source) as f:
                self._extra_files[destination] = f.read()
        else:
            self._extra_files[destination] = source

    def add_directory(self, source: str, destination: str) -> None:
        """Adds a directory to the build context.

        Args:
            source: Path to the directory.
            destination: The path inside the build context where the directory
                should be added.

        Raises:
            ValueError: If `source` does not point to a directory.
        """
        if not fileio.isdir(source):
            raise ValueError(
                f"Can't add directory {source} to the build context as it "
                "does not exist or is not a directory."
            )

        for dir, _, files in fileio.walk(source):
            dir_path = Path(fileio.convert_to_str(dir))
            for file_name in files:
                file_name = fileio.convert_to_str(file_name)
                file_source = dir_path / file_name
                file_destination = (
                    Path(destination)
                    / dir_path.relative_to(source)
                    / file_name
                )

                with file_source.open("r") as f:
                    self._extra_files[file_destination.as_posix()] = f.read()

    def create_archive(
        self,
        files: List[str],
        fileobj: IO[bytes],
        extra_files: List[Tuple[str, str]],
        archive_type: ArchiveType,
    ) -> None:
        """Creates an archive of the build context.

        Args:
            files: The files to include in the archive.
            fileobj: The file object to write the archive to.
            extra_files: Extra files to include in the archive.
            archive_type: The type of archive to create.
        """
        if archive_type in [ArchiveType.TAR, ArchiveType.TAR_GZ]:
            from docker.utils import build as docker_build_utils

            docker_build_utils.create_archive(
                fileobj=fileobj,
                root=self._root,
                files=files,
                gzip=archive_type == ArchiveType.TAR_GZ,
                extra_files=extra_files,
            )
            return

        z = zipfile.ZipFile(fileobj, "w", zipfile.ZIP_DEFLATED)
        extra_names = {e[0] for e in extra_files}
        if self._root:
            for path in files:
                if path in extra_names:
                    continue
                full_path = os.path.join(self._root, path)
                if os.path.isfile(full_path):
                    try:
                        z.write(full_path, arcname=path)
                    except OSError:
                        raise OSError(
                            f"Can not read file in context: {full_path}"
                        )
                else:
                    # Add directories to the zip file
                    z.write(full_path, arcname=path)

        for name, contents in extra_files:
            contents_encoded = contents.encode("utf-8")
            z.writestr(name, contents_encoded)

        z.close()
        fileobj.seek(0)

    def write_archive(
        self,
        output_file: IO[bytes],
        archive_type: ArchiveType = ArchiveType.TAR_GZ,
    ) -> None:
        """Writes an archive of the build context to the given file.

        Args:
            output_file: The file to write the archive to.
            archive_type: The type of archive to create.
        """
        files = self._get_files()
        extra_files = self._get_extra_files()

        self.create_archive(
            fileobj=output_file,
            files=sorted(files),
            extra_files=extra_files,
            archive_type=archive_type,
        )

        build_context_size = os.path.getsize(output_file.name)
        if (
            self._root
            and build_context_size > 50 * 1024 * 1024
            and not self.dockerignore_file
        ):
            # The build context exceeds 50MiB and we didn't find any excludes
            # in dockerignore files -> remind to specify a .dockerignore file
            logger.warning(
                "Build context size for docker image: `%s`. If you believe this is "
                "unreasonably large, make sure to include a `.dockerignore` file "
                "at the root of your build context `%s` or specify a custom file "
                "in the Docker configuration when defining your pipeline.",
                string_utils.get_human_readable_filesize(build_context_size),
                os.path.join(self._root, ".dockerignore"),
            )

    def _get_files(self) -> Set[str]:
        """Gets all non-ignored files in the build context root directory.

        Returns:
            All build context files.
        """
        if self._root:
            exclude_patterns = self._get_exclude_patterns()
            from docker.utils import build as docker_build_utils

            return cast(
                Set[str],
                docker_build_utils.exclude_paths(
                    self._root, patterns=exclude_patterns
                ),
            )
        else:
            return set()

    def _get_extra_files(self) -> List[Tuple[str, str]]:
        """Gets all extra files of the build context.

        Returns:
            A tuple (path, file_content) for all extra files in the build
            context.
        """
        return list(self._extra_files.items())

    def _get_exclude_patterns(self) -> List[str]:
        """Gets all exclude patterns from the dockerignore file.

        Returns:
            The exclude patterns from the dockerignore file.
        """
        dockerignore = self.dockerignore_file
        if dockerignore:
            patterns = self._parse_dockerignore(dockerignore)
            # Always include the .zen directory
            patterns.append(f"!/{REPOSITORY_DIRECTORY_NAME}")
            return patterns
        else:
            logger.info(
                "No `.dockerignore` found, including all files inside build "
                "context.",
            )
            return []

    @staticmethod
    def _parse_dockerignore(dockerignore_path: str) -> List[str]:
        """Parses a dockerignore file and returns a list of patterns to ignore.

        Args:
            dockerignore_path: Path to the dockerignore file.

        Returns:
            List of patterns to ignore.
        """
        try:
            file_content = io_utils.read_file_contents_as_string(
                dockerignore_path
            )
        except FileNotFoundError:
            logger.warning(
                "Unable to find dockerignore file at path '%s'.",
                dockerignore_path,
            )
            return []

        exclude_patterns = []
        for line in file_content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                exclude_patterns.append(line)

        return exclude_patterns
