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

import os
from typing import IO, Dict, List, Optional, Set, cast

from zenml.constants import REPOSITORY_DIRECTORY_NAME
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import io_utils, string_utils
from zenml.utils.archivable import Archivable

logger = get_logger(__name__)


class BuildContext(Archivable):
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
        super().__init__()
        self._root = root
        self._dockerignore_file = dockerignore_file

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

    def write_archive(
        self, output_file: IO[bytes], use_gzip: bool = True
    ) -> None:
        """Writes an archive of the build context to the given file.

        Args:
            output_file: The file to write the archive to.
            use_gzip: Whether to use `gzip` to compress the file.
        """
        from docker.utils import build as docker_build_utils

        files = self.get_files()
        extra_files = self.get_extra_files()

        context_archive = docker_build_utils.create_archive(
            fileobj=output_file,
            root=self._root,
            files=sorted(files.keys()),
            gzip=use_gzip,
            extra_files=list(extra_files.items()),
        )

        build_context_size = os.path.getsize(context_archive.name)
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

    def get_files(self) -> Dict[str, str]:
        """Gets all regular files that should be included in the archive.

        Returns:
            A dict {path_in_archive: path_on_filesystem} for all regular files
            in the archive.
        """
        if self._root:
            from docker.utils import build as docker_build_utils

            exclude_patterns = self._get_exclude_patterns()

            archive_paths = cast(
                Set[str],
                docker_build_utils.exclude_paths(
                    self._root, patterns=exclude_patterns
                ),
            )
            return {
                archive_path: os.path.join(self._root, archive_path)
                for archive_path in archive_paths
            }
        else:
            return {}

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
