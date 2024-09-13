#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Code archive."""

import os
from pathlib import Path
from typing import IO, TYPE_CHECKING, Dict, Optional

from zenml.logger import get_logger
from zenml.utils import string_utils
from zenml.utils.archivable import Archivable

if TYPE_CHECKING:
    from git.repo.base import Repo


logger = get_logger(__name__)


class CodeArchive(Archivable):
    """Code archive class.

    This class is used to archive user code before uploading it to the artifact
    store. If the user code is stored in a Git repository, only files not
    excluded by gitignores will be included in the archive.
    """

    def __init__(self, root: str) -> None:
        """Initialize the object.

        Args:
            root: Root directory of the archive.
        """
        super().__init__()
        self._root = root

    @property
    def git_repo(self) -> Optional["Repo"]:
        """Git repository active at the code archive root.

        Returns:
            The git repository if available.
        """
        try:
            # These imports fail when git is not installed on the machine
            from git.exc import InvalidGitRepositoryError
            from git.repo.base import Repo
        except ImportError:
            return None

        try:
            git_repo = Repo(path=self._root, search_parent_directories=True)
        except InvalidGitRepositoryError:
            return None

        return git_repo

    def _get_all_files(self) -> Dict[str, str]:
        """Get all files inside the archive root.

        Returns:
            All files inside the archive root.
        """
        all_files = {}
        for root, _, files in os.walk(self._root):
            for file in files:
                file_path = os.path.join(root, file)
                path_in_archive = os.path.relpath(file_path, self._root)
                all_files[path_in_archive] = file_path

        return all_files

    def get_files(self) -> Dict[str, str]:
        """Gets all regular files that should be included in the archive.

        Raises:
            RuntimeError: If the code archive would not include any files.

        Returns:
            A dict {path_in_archive: path_on_filesystem} for all regular files
            in the archive.
        """
        all_files = {}

        if repo := self.git_repo:
            try:
                result = repo.git.ls_files(
                    "--cached",
                    "--others",
                    "--modified",
                    "--exclude-standard",
                    self._root,
                )
            except Exception as e:
                logger.warning(
                    "Failed to get non-ignored files from git: %s", str(e)
                )
                all_files = self._get_all_files()
            else:
                for file in result.split():
                    file_path = os.path.join(repo.working_dir, file)
                    path_in_archive = os.path.relpath(file_path, self._root)

                    if os.path.exists(file_path):
                        all_files[path_in_archive] = file_path
        else:
            all_files = self._get_all_files()

        if not all_files:
            raise RuntimeError(
                "The code archive to be uploaded does not contain any files. "
                "This is probably because all files in your source root "
                f"`{self._root}` are ignored by a .gitignore file."
            )

        # Explicitly remove .zen directories as we write an updated version
        # to disk everytime ZenML is called. This updates the mtime of the
        # file, which invalidates the code upload caching. The values in
        # the .zen directory are not needed anyway as we set them as
        # environment variables.
        all_files = {
            path_in_archive: file_path
            for path_in_archive, file_path in sorted(all_files.items())
            if ".zen" not in Path(path_in_archive).parts[:-1]
        }

        return all_files

    def write_archive(
        self, output_file: IO[bytes], use_gzip: bool = True
    ) -> None:
        """Writes an archive of the build context to the given file.

        Args:
            output_file: The file to write the archive to.
            use_gzip: Whether to use `gzip` to compress the file.
        """
        super().write_archive(output_file=output_file, use_gzip=use_gzip)
        archive_size = os.path.getsize(output_file.name)
        if archive_size > 20 * 1024 * 1024:
            logger.warning(
                "Code archive size: `%s`. If you believe this is "
                "unreasonably large, make sure to version your code in git and "
                "ignore unnecessary files using a `.gitignore` file.",
                string_utils.get_human_readable_filesize(archive_size),
            )
