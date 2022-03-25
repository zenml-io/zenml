import os
import tarfile
from pathlib import Path
from typing import Callable, Optional

import click

from zenml.constants import APP_NAME, ENV_ZENML_CONFIG_PATH
from zenml.io.fileio import file_exists, is_remote, open


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


def get_global_config_directory() -> str:
    """Returns the global config directory for ZenML."""
    env_var_path = os.getenv(ENV_ZENML_CONFIG_PATH)
    if env_var_path:
        return str(Path(env_var_path).resolve())
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
