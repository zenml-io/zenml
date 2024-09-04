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
"""Code utilities."""

import hashlib
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import IO, TYPE_CHECKING, Dict, Optional

from zenml.client import Client
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import source_utils, string_utils
from zenml.utils.archivable import Archivable

if TYPE_CHECKING:
    from git.repo.base import Repo

    from zenml.artifact_stores import BaseArtifactStore


logger = get_logger(__name__)


class CodeArchive(Archivable):
    """Code archive class.

    This class is used to archive user code before uploading it to the artifact
    store. If the user code is stored in a Git repository, only files not
    excluded by gitignores will be included in the archive.
    """

    def __init__(self, root: Optional[str] = None) -> None:
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

    def _get_all_files(self, archive_root: str) -> Dict[str, str]:
        """Get all files inside the archive root.

        Args:
            archive_root: The root directory from which to get all files.

        Returns:
            All files inside the archive root.
        """
        all_files = {}
        for root, _, files in os.walk(archive_root):
            for file in files:
                file_path = os.path.join(root, file)
                path_in_archive = os.path.relpath(file_path, archive_root)
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
        if not self._root:
            return {}

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
                all_files = self._get_all_files(archive_root=self._root)
            else:
                for file in result.split():
                    file_path = os.path.join(repo.working_dir, file)
                    path_in_archive = os.path.relpath(file_path, self._root)

                    if os.path.exists(file_path):
                        all_files[path_in_archive] = file_path
        else:
            all_files = self._get_all_files(archive_root=self._root)

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


def compute_file_hash(file: IO[bytes]) -> str:
    """Compute a hash of the content of a file.

    This function will not seek the file before or after the hash computation.
    This means that the content will be computed based on the current cursor
    until the end of the file.

    Args:
        file: The file for which to compute the hash.

    Returns:
        A hash of the file content.
    """
    hash_ = hashlib.sha1()  # nosec

    while True:
        data = file.read(64 * 1024)
        if not data:
            break
        hash_.update(data)

    return hash_.hexdigest()


def upload_code_if_necessary(code_archive: CodeArchive) -> str:
    """Upload code to the artifact store if necessary.

    This function computes a hash of the code to be uploaded, and if an archive
    with the same hash already exists it will not re-upload but instead return
    the path to the existing archive.

    Args:
        code_archive: The code archive to upload.

    Returns:
        The path where the archived code is uploaded.
    """
    artifact_store = Client().active_stack.artifact_store

    with tempfile.NamedTemporaryFile(
        mode="w+b", delete=False, suffix=".tar.gz"
    ) as f:
        code_archive.write_archive(f)
        archive_path = f.name
        archive_hash = compute_file_hash(f)

    upload_dir = os.path.join(artifact_store.path, "code_uploads")
    fileio.makedirs(upload_dir)
    upload_path = os.path.join(upload_dir, f"{archive_hash}.tar.gz")

    if not fileio.exists(upload_path):
        archive_size = string_utils.get_human_readable_filesize(
            os.path.getsize(archive_path)
        )
        logger.info(
            "Uploading code to `%s` (Size: %s).", upload_path, archive_size
        )
        fileio.copy(archive_path, upload_path)
        logger.info("Code upload finished.")
    else:
        logger.info("Code already exists in artifact store, skipping upload.")

    if os.path.exists(archive_path):
        os.remove(archive_path)

    return upload_path


def download_and_extract_code(code_path: str, extract_dir: str) -> None:
    """Download and extract code.

    Args:
        code_path: Path where the code is uploaded.
        extract_dir: Directory where to code should be extracted to.

    Raises:
        RuntimeError: If the code is stored in an artifact store which is
            not active.
    """
    artifact_store = Client().active_stack.artifact_store

    if not code_path.startswith(artifact_store.path):
        raise RuntimeError("Code stored in different artifact store.")

    download_path = os.path.basename(code_path)
    fileio.copy(code_path, download_path)

    shutil.unpack_archive(filename=download_path, extract_dir=extract_dir)
    os.remove(download_path)


def download_code_from_artifact_store(code_path: str) -> None:
    """Download code from the artifact store.

    Args:
        code_path: Path where the code is stored.
    """
    logger.info("Downloading code from artifact store path `%s`.", code_path)

    # Do not remove this line, we need to instantiate the artifact store to
    # register the filesystem needed for the file download
    _ = Client().active_stack.artifact_store

    extract_dir = os.path.abspath("code")
    os.makedirs(extract_dir)

    download_and_extract_code(code_path=code_path, extract_dir=extract_dir)

    source_utils.set_custom_source_root(extract_dir)
    sys.path.insert(0, extract_dir)
    os.chdir(extract_dir)


def _get_notebook_upload_dir(artifact_store: "BaseArtifactStore") -> str:
    """Get the upload directory for code extracted from notebook cells.

    Args:
        artifact_store: The artifact store in which the directory should be.

    Returns:
        The upload directory for code extracted from notebook cells.
    """
    return os.path.join(artifact_store.path, "notebook_code")


def upload_notebook_code(
    artifact_store: "BaseArtifactStore", cell_code: str, file_name: str
) -> None:
    """Upload code extracted from a notebook cell.

    Args:
        artifact_store: The artifact store in which to upload the code.
        cell_code: The notebook cell code.
        file_name: The filename to use for storing the cell code.
    """
    upload_dir = _get_notebook_upload_dir(artifact_store=artifact_store)
    fileio.makedirs(upload_dir)
    upload_path = os.path.join(upload_dir, file_name)

    if not fileio.exists(upload_path):
        with fileio.open(upload_path, "wb") as f:
            f.write(cell_code.encode())

        logger.info("Uploaded notebook cell code to %s.", upload_path)


def download_notebook_code(
    artifact_store: "BaseArtifactStore", file_name: str, download_path: str
) -> None:
    """Download code extracted from a notebook cell.

    Args:
        artifact_store: The artifact store from which to download the code.
        file_name: The name of the code file.
        download_path: The local path where the file should be downloaded to.

    Raises:
        FileNotFoundError: If no file with the given filename exists in this
            artifact store.
    """
    code_dir = _get_notebook_upload_dir(artifact_store=artifact_store)
    code_path = os.path.join(code_dir, file_name)

    if not fileio.exists(code_path):
        raise FileNotFoundError(
            f"Notebook code at path {code_path} not found."
        )

    fileio.copy(code_path, download_path)
