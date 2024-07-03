import os
import subprocess
import tempfile
from abc import ABC

from zenml.io import fileio
from zenml.orchestrators import BaseOrchestrator
from zenml.utils.io_utils import copy_dir
from zenml.utils.source_utils import get_source_root


class WheeledOrchestrator(BaseOrchestrator, ABC):
    """Base class for wheeled orchestrators."""

    PACKAGE_NAME = "zenmlproject"

    def copy_repository_to_temp_dir_and_add_setup_py(self) -> str:
        """Copy the repository to a temporary directory and add a setup.py file."""
        repo_path = get_source_root()

        # Create a temporary folder
        temp_dir = tempfile.mkdtemp(prefix="zenml-temp-")

        # Create a folder within the temporary directory
        temp_repo_path = os.path.join(temp_dir, self.PACKAGE_NAME)
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
    name="{self.PACKAGE_NAME}",
    version="0.1",
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
            print(f"Wheel creation stdout: {result.stdout.decode()}")
            print(f"Wheel creation stderr: {result.stderr.decode()}")

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
