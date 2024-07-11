#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Wheeled orchestrator class."""

import os
import re
import subprocess
import tempfile
from abc import ABC

from zenml import __version__
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestrator
from zenml.utils.io_utils import copy_dir
from zenml.utils.source_utils import get_source_root

logger = get_logger(__name__)

DEFAULT_PACKAGE_NAME = "zenmlproject"


class WheeledOrchestrator(BaseOrchestrator, ABC):
    """Base class for wheeled orchestrators."""

    package_name = DEFAULT_PACKAGE_NAME
    package_version = __version__

    def copy_repository_to_temp_dir_and_add_setup_py(self) -> str:
        """Copy the repository to a temporary directory and add a setup.py file.

        Returns:
            Path to the temporary directory containing the copied repository.
        """
        repo_path = get_source_root()

        self.package_name = f"{DEFAULT_PACKAGE_NAME}_{self.sanitize_name(os.path.basename(repo_path))}"

        # Create a temporary folder
        temp_dir = tempfile.mkdtemp(prefix="zenml-temp-")

        # Create a folder within the temporary directory
        temp_repo_path = os.path.join(temp_dir, self.package_name)
        fileio.mkdir(temp_repo_path)

        # Copy the repository to the temporary directory
        copy_dir(repo_path, temp_repo_path)

        # Create init file in the copied directory
        init_file_path = os.path.join(temp_repo_path, "__init__.py")
        with fileio.open(init_file_path, "w") as f:
            f.write("")

        # Create a setup.py file
        setup_py_content = f"""
from setuptools import setup, find_packages

setup(
    name="{self.package_name}",
    version="{self.package_version}",
    packages=find_packages(),
)
"""
        setup_py_path = os.path.join(temp_dir, "setup.py")
        with fileio.open(setup_py_path, "w") as f:
            f.write(setup_py_content)

        return temp_dir

    def create_wheel(self, temp_dir: str) -> str:
        """Create a wheel for the package in the given temporary directory.

        Args:
            temp_dir (str): Path to the temporary directory containing the package.

        Returns:
            str: Path to the created wheel file.
        """
        # Change to the temporary directory
        original_dir = os.getcwd()
        os.chdir(temp_dir)

        try:
            # Run the `pip wheel` command to create the wheel
            result = subprocess.run(
                ["pip", "wheel", "."], check=True, capture_output=True
            )
            logger.debug(f"Wheel creation stdout: {result.stdout.decode()}")
            logger.debug(f"Wheel creation stderr: {result.stderr.decode()}")

            # Find the created wheel file
            wheel_file = next(
                (
                    file
                    for file in os.listdir(temp_dir)
                    if file.endswith(".whl")
                ),
                None,
            )

            if wheel_file is None:
                raise RuntimeError("Failed to create wheel file.")

            wheel_path = os.path.join(temp_dir, wheel_file)

            # Verify the wheel file is a valid zip file
            import zipfile

            if not zipfile.is_zipfile(wheel_path):
                raise RuntimeError(
                    f"The file {wheel_path} is not a valid zip file."
                )

            return wheel_path
        finally:
            # Change back to the original directory
            os.chdir(original_dir)

    def sanitize_name(self, name: str) -> str:
        """Sanitize the value to be used in a cluster name.

        Args:
            name: Arbitrary input cluster name.

        Returns:
            Sanitized cluster name.
        """
        name = re.sub(
            r"[^a-z0-9-]", "-", name.lower()
        )  # replaces any character that is not a lowercase letter, digit, or hyphen with a hyphen
        name = re.sub(r"^[-]+", "", name)  # trim leading hyphens
        name = re.sub(r"[-]+$", "", name)  # trim trailing hyphens
        return name
