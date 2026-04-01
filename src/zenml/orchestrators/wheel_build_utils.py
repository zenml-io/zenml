#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Helpers for packaging the current source tree as a wheel."""

import os
import re
import subprocess
import tempfile
import zipfile

from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils.io_utils import copy_dir
from zenml.utils.source_utils import get_source_root

logger = get_logger(__name__)

DEFAULT_PACKAGE_NAME = "zenmlproject"


def sanitize_name(name: str) -> str:
    """Sanitize a name for use in generated package identifiers.

    Args:
        name: Arbitrary input name.

    Returns:
        Sanitized name.
    """
    name = re.sub(r"[^a-z0-9-]", "-", name.lower())
    name = re.sub(r"^[-]+", "", name)
    name = re.sub(r"[-]+$", "", name)
    return name


def get_wheel_package_name() -> str:
    """Generate the package name used for the temporary project wheel.

    Returns:
        The generated package name.
    """
    repo_path = get_source_root()
    return (
        f"{DEFAULT_PACKAGE_NAME}_{sanitize_name(os.path.basename(repo_path))}"
    )


def prepare_repository_copy_for_wheel(
    package_name: str,
    package_version: str,
) -> str:
    """Copy the repository to a temporary directory and add a setup.py file.

    Args:
        package_name: Name for the generated wheel package.
        package_version: Version for the generated wheel package.

    Returns:
        Path to the temporary directory containing the copied repository.
    """
    repo_path = get_source_root()

    temp_dir = tempfile.mkdtemp(prefix="zenml-temp-")
    temp_repo_path = os.path.join(temp_dir, package_name)
    fileio.mkdir(temp_repo_path)
    copy_dir(repo_path, temp_repo_path)

    init_file_path = os.path.join(temp_repo_path, "__init__.py")
    with fileio.open(init_file_path, "w") as f:
        f.write("")

    setup_py_content = f"""
from setuptools import setup, find_packages

setup(
    name="{package_name}",
    version="{package_version}",
    packages=find_packages(),
)
"""
    setup_py_path = os.path.join(temp_dir, "setup.py")
    with fileio.open(setup_py_path, "w") as f:
        f.write(setup_py_content)

    return temp_dir


def create_wheel(temp_dir: str) -> str:
    """Create a wheel for a copied repository directory.

    Args:
        temp_dir: Path to the temporary directory containing the package.

    Raises:
        RuntimeError: If the wheel file could not be created.

    Returns:
        Path to the created wheel file.
    """
    original_dir = os.getcwd()
    os.chdir(temp_dir)

    try:
        result = subprocess.run(
            ["pip", "wheel", "."], check=True, capture_output=True
        )
        logger.debug(f"Wheel creation stdout: {result.stdout.decode()}")
        logger.debug(f"Wheel creation stderr: {result.stderr.decode()}")

        wheel_file = next(
            (file for file in os.listdir(temp_dir) if file.endswith(".whl")),
            None,
        )

        if wheel_file is None:
            raise RuntimeError("Failed to create wheel file.")

        wheel_path = os.path.join(temp_dir, wheel_file)
        if not zipfile.is_zipfile(wheel_path):
            raise RuntimeError(
                f"The file {wheel_path} is not a valid zip file."
            )

        return wheel_path
    finally:
        os.chdir(original_dir)
