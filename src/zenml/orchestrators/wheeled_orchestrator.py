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

from abc import ABC

from zenml import __version__
from zenml.orchestrators.base_orchestrator import BaseOrchestrator
from zenml.orchestrators.wheel_build_utils import (
    DEFAULT_PACKAGE_NAME,
    create_wheel,
    get_wheel_package_name,
    prepare_repository_copy_for_wheel,
    sanitize_name,
)


class WheeledOrchestrator(BaseOrchestrator, ABC):
    """Base class for wheeled orchestrators."""

    package_name = DEFAULT_PACKAGE_NAME
    package_version = __version__

    def copy_repository_to_temp_dir_and_add_setup_py(self) -> str:
        """Copy the repository to a temporary directory and add a setup.py file.

        Returns:
            Path to the temporary directory containing the copied repository.
        """
        self.package_name = get_wheel_package_name()
        return prepare_repository_copy_for_wheel(
            package_name=self.package_name,
            package_version=self.package_version,
        )

    def create_wheel(self, temp_dir: str) -> str:
        """Create a wheel for the package in the given temporary directory.

        Args:
            temp_dir: Path to the temporary directory containing the package.

        Returns:
            Path to the created wheel file.
        """
        return create_wheel(temp_dir=temp_dir)

    def sanitize_name(self, name: str) -> str:
        """Sanitize the value to be used in a cluster name.

        Args:
            name: Arbitrary input cluster name.

        Returns:
            Sanitized cluster name.
        """
        return sanitize_name(name)
