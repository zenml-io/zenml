import os
import tarfile
from pathlib import Path
from typing import Callable, Optional

import click

from zenml.constants import APP_NAME, ENV_ZENML_REPOSITORY_PATH
from zenml.core.constants import ZENML_DIR_NAME
from zenml.exceptions import InitializationException
from zenml.io.fileio import file_exists, is_dir, is_remote, is_root, open


def create_tarfile(
    source_dir: str,
    output_filename: str = "zipped.tar.gz",
    exclude_function: Optional[
        Callable[[tarfile.TarInfo], Optional[tarfile.TarInfo]]
    ] = None,
) -> None:
    """Create a compressed representation of source_dir.

    Args:
        source_dir: Path to source dir.
        output_filename: Name of outputted gz.
        exclude_function: Function that determines whether to exclude file.
    """
    if exclude_function is None:
        # default is to exclude the .zenml directory
        def exclude_function(
            tarinfo: tarfile.TarInfo,
        ) -> Optional[tarfile.TarInfo]:
            """Exclude files from tar.

            Args:
              tarinfo: Any

            Returns:
                tarinfo required for exclude.
            """
            filename = tarinfo.name
            if ".zenml/" in filename or "venv/" in filename:
                return None
            else:
                return tarinfo

    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname="", filter=exclude_function)


def extract_tarfile(source_tar: str, output_dir: str) -> None:
    """Extracts all files in a compressed tar file to output_dir.

    Args:
        source_tar: Path to a tar compressed file.
        output_dir: Directory where to extract.
    """
    if is_remote(source_tar):
        raise NotImplementedError("Use local tars for now.")

    with tarfile.open(source_tar, "r:gz") as tar:
        tar.extractall(output_dir)


def is_zenml_dir(path: str) -> bool:
    """Check if dir is a zenml dir or not.

    Args:
        path: Path to the root.

    Returns:
        True if path contains a zenml dir, False if not.
    """
    config_dir_path = os.path.join(path, ZENML_DIR_NAME)
    return bool(is_dir(config_dir_path))


def get_zenml_config_dir(path: Optional[str] = None) -> str:
    """Recursive function to find the zenml config starting from path.

    Args:
        path (Default value = os.getcwd()): Path to check.

    Returns:
        The full path with the resolved zenml directory.

    Raises:
        InitializationException if directory not found until root of OS.
    """
    return os.path.join(get_zenml_dir(path), ZENML_DIR_NAME)


def get_zenml_dir(path: Optional[str] = None) -> str:
    """Returns path to a ZenML repository directory.

    Args:
        path: Optional path to look for the repository. If no path is given,
            this function tries to find the repository using the environment
            variable `ZENML_REPOSITORY_PATH` (if set) and recursively searching
            in the parent directories of the current working directory.

    Returns:
        Absolute path to a ZenML repository directory.

    Raises:
        InitializationException: If no ZenML repository is found.
    """
    if not path:
        # try to get path from the environment variable
        path = os.getenv(ENV_ZENML_REPOSITORY_PATH, None)

    if path:
        # explicit path via parameter or environment variable, don't search
        # parent directories
        search_parent_directories = False
        error_message = (
            f"Unable to find ZenML repository at path '{path}'. Make sure to "
            f"create a ZenML repository by calling `zenml init` when "
            f"specifying an explicit repository path in code or via the "
            f"environment variable '{ENV_ZENML_REPOSITORY_PATH}'."
        )
    else:
        # try to find the repo in the parent directories of the
        # current working directory
        path = os.getcwd()
        search_parent_directories = True
        error_message = (
            f"Unable to find ZenML repository in your current working "
            f"directory ({os.getcwd()}) or any parent directories. If you "
            f"want to use an existing repository which is in a different "
            f"location, set the environment variable "
            f"'{ENV_ZENML_REPOSITORY_PATH}'. If you want to create a new "
            f"repository, run `zenml init`."
        )

    def _find_repo_helper(repo_path: str) -> str:
        """Helper function to recursively search parent directories for a
        ZenML repository."""
        if is_zenml_dir(repo_path):
            return repo_path

        if not search_parent_directories or is_root(repo_path):
            raise InitializationException(error_message)

        return _find_repo_helper(str(Path(repo_path).parent))

    path = _find_repo_helper(path)
    return str(Path(path).resolve())


def get_global_config_directory() -> str:
    """Returns the global config directory for ZenML."""
    return click.get_app_dir(APP_NAME)


def write_file_contents_as_string(file_path: str, content: str) -> None:
    """Writes contents of file.

    Args:
        file_path: Path to file.
        content: Contents of file.
    """
    with open(file_path, "w") as f:
        f.write(content)


def read_file_contents_as_string(file_path: str) -> str:
    """Reads contents of file.

    Args:
        file_path: Path to file.
    """
    if not file_exists(file_path):
        raise FileNotFoundError(f"{file_path} does not exist!")
    return open(file_path).read()  # type: ignore[no-any-return]


def is_gcs_path(path: str) -> bool:
    """Returns True if path is on Google Cloud Storage.

    Args:
        path: Any path as a string.

    Returns:
        True if gcs path, else False.
    """
    return path.startswith("gs://")
