#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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

from abc import ABC
import os
import tempfile
from typing import List, Optional
import subprocess

from zenml.config.build_configuration import BuildConfiguration
from zenml.constants import ORCHESTRATOR_DOCKER_IMAGE_KEY
from zenml.io import fileio
from zenml.models import PipelineDeploymentBase, PipelineDeploymentResponse
from zenml.orchestrators import BaseOrchestrator
from zenml.utils.io_utils import copy_dir
from zenml.utils.source_utils import get_source_root


class WheeledOrchestrator(BaseOrchestrator, ABC):
    """Base class for wheeled orchestrators."""

    @staticmethod
    def copy_repository_to_temp_dir_and_add_setup_py() -> str:
        """Copy the repository to a temporary directory and add a setup.py file.
        """
        repo_path = get_source_root()
        
        # Create a temporary folder
        temp_dir = tempfile.mkdtemp(prefix="zenml-temp-")

        # Create a folder within the temporary directory
        temp_repo_path = os.path.join(temp_dir, "zenmlproject")

        fileio.mkdir(temp_repo_path)

        # Copy the repository to the temporary directory
        copy_dir(repo_path, temp_repo_path)

        # create init file in the copied directory
        init_file_path = os.path.join(temp_repo_path, "__init__.py")
        with fileio.open(init_file_path, "w") as f:
            f.write("")

        # Create a setup.py file
        setup_py_content = f"""
from setuptools import setup, find_packages

setup(
    name="zenmlproject",
    version="0.1",
    packages=find_packages(),
)
"""
        setup_py_path = os.path.join(temp_dir, "setup.py")
        with fileio.open(setup_py_path, "w") as f:
            f.write(setup_py_content)

        return temp_dir

    @staticmethod
    def create_wheel(temp_dir: str) -> str:
        """
        Create a wheel for the package in the given temporary directory.

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
            subprocess.run(["pip", "wheel", "."], check=True)

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
            return wheel_path
        finally:
            # Change back to the original directory
            os.chdir(original_dir)


