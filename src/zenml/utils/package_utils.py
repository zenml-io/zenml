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
"""Utility functions for the package."""

import sys
from typing import Dict, List, Optional, Union, cast

import requests
from packaging import version
from packaging.markers import default_environment
from packaging.requirements import Requirement

if sys.version_info < (3, 10):
    from importlib_metadata import (
        PackageNotFoundError,
        distribution,
        distributions,
    )
else:
    from importlib.metadata import (
        PackageNotFoundError,
        distribution,
        distributions,
    )


def is_latest_zenml_version() -> bool:
    """Checks if the currently running ZenML package is on the latest version.

    Returns:
        True in case the current running zenml code is the latest available version on PYPI, otherwise False.

    Raises:
        RuntimeError: In case something goe wrong
    """
    from zenml import __version__

    # Get the current version of the package
    current_local_version = __version__

    # Get the latest version from PyPI
    try:
        response = requests.get("https://pypi.org/pypi/zenml/json", timeout=60)
        response.raise_for_status()
        latest_published_version = response.json()["info"]["version"]
    except Exception as e:
        raise RuntimeError(
            f"Failed to fetch the latest version from PyPI: {e}"
        )

    # Compare versions
    if version.parse(latest_published_version) > version.parse(
        current_local_version
    ):
        return False
    else:
        return True


def clean_requirements(requirements: List[str]) -> List[str]:
    """Clean requirements list from redundant requirements.

    Args:
        requirements: List of requirements.

    Returns:
        Cleaned list of requirements

    Raises:
        TypeError: If input is not a list
        ValueError: If any element in the list is not a string
    """
    if not isinstance(requirements, list):
        raise TypeError("Input must be a list")

    if not all(isinstance(req, str) for req in requirements):
        raise ValueError("All elements in the list must be strings")

    cleaned = {}
    for req in requirements:
        package = (
            req.split(">=")[0]
            .split("==")[0]
            .split("<")[0]
            .split("~=")[0]
            .split("^=")[0]
            .split("[")[0]
            .strip()
        )
        if package not in cleaned or any(
            op in req for op in ["=", ">", "<", "~", "^"]
        ):
            cleaned[package] = req
    return sorted(cleaned.values())


def requirement_installed(requirement: Union[str, Requirement]) -> bool:
    """Check if a requirement is installed.

    Args:
        requirement: A requirement string.

    Returns:
        True if the requirement is installed, False otherwise.
    """
    if isinstance(requirement, str):
        requirement = Requirement(requirement)

    try:
        dist = distribution(requirement.name)
    except PackageNotFoundError:
        return False

    return requirement.specifier.contains(dist.version)


def get_dependencies(
    requirement: Requirement, recursive: bool = False
) -> List[Requirement]:
    """Get the dependencies of a requirement.

    Args:
        requirement: A requirement string.
        recursive: Whether to include recursive dependencies.

    Returns:
        A list of requirements.
    """
    dist = distribution(requirement.name)
    marker_environment = cast(Dict[str, str], default_environment())

    dependencies = []

    for req in dist.requires or []:
        parsed_req = Requirement(req)

        if parsed_req.marker:
            should_include = False

            marker_environment["extra"] = ""
            if parsed_req.marker.evaluate(environment=marker_environment):
                should_include = True

            if not should_include:
                # Not required without extras, so check if it's required with
                # any of the requested extras
                for extra in requirement.extras:
                    marker_environment["extra"] = extra
                    if parsed_req.marker.evaluate(
                        environment=marker_environment
                    ):
                        should_include = True
                        break

            if should_include:
                dependencies.append(parsed_req)
        else:
            # No marker means always include
            dependencies.append(parsed_req)

    if recursive:
        for dependency in dependencies:
            dependencies.extend(get_dependencies(dependency, recursive=True))

    return dependencies


def get_package_information(
    package_names: Optional[List[str]] = None,
) -> Dict[str, str]:
    """Get package information.

    Args:
        package_names: Filter for specific package names. If no package names
            are provided, all installed packages are returned.

    Returns:
        A dictionary of the name:version for the package names passed in or
            all packages and their respective versions.
    """
    if package_names:
        return {
            dist.name: dist.version
            for dist in distributions()
            if dist.name in package_names
        }

    return {dist.name: dist.version for dist in distributions()}
