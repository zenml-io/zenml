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

from typing import List

import requests
from packaging import version


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
    """
    cleaned = {}
    for req in requirements:
        package = (
            req.split(">=")[0]
            .split("==")[0]
            .split("<")[0]
            .split("[")[0]
            .strip()
        )
        if package not in cleaned or ("=" in req or ">" in req or "<" in req):
            cleaned[package] = req
    return sorted(cleaned.values())
