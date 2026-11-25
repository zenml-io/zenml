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
"""Requirement utils."""

from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Iterable, List, Optional, Set, Tuple

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from zenml.integrations.utils import get_integration_for_module

if TYPE_CHECKING:
    from zenml.models import ComponentResponse, StackResponse


def get_requirements_for_stack(
    stack: "StackResponse",
    python_version: Optional[str] = None,
) -> Tuple[List[str], List[str]]:
    """Get requirements for a stack model.

    Args:
        stack: The stack for which to get the requirements.
        python_version: The Python version to use for the requirements.

    Returns:
        Tuple of PyPI and APT requirements of the stack.
    """
    pypi_requirements: Set[str] = set()
    apt_packages: Set[str] = set()

    for component_list in stack.components.values():
        assert len(component_list) == 1
        component = component_list[0]
        (
            component_pypi_requirements,
            component_apt_packages,
        ) = get_requirements_for_component(
            component=component,
            python_version=python_version,
        )
        pypi_requirements = pypi_requirements.union(
            component_pypi_requirements
        )
        apt_packages = apt_packages.union(component_apt_packages)

    return sorted(pypi_requirements), sorted(apt_packages)


def get_requirements_for_component(
    component: "ComponentResponse",
    python_version: Optional[str] = None,
) -> Tuple[List[str], List[str]]:
    """Get requirements for a component model.

    Args:
        component: The component for which to get the requirements.
        python_version: The Python version to use for the requirements.

    Returns:
        Tuple of PyPI and APT requirements of the component.
    """
    integration = get_integration_for_module(
        module_name=component.flavor.source
    )

    if integration:
        return integration.get_requirements(
            python_version=python_version
        ), integration.APT_PACKAGES
    else:
        return [], []


# pip and uv only resolve the packages they are asked to install, not the ones
# that are already installed. Installing other packages can therefore replace
# ZenML dependencies with versions ZenML doesn't support, e.g. a newer
# `fastapi` upgrading `opentelemetry-api` past what the pinned
# `opentelemetry-sdk` supports. Adding the installed ZenML version to an install
# makes the resolver respect ZenML's requirements. Since that version is
# already installed, this works for unreleased versions too.

# Shell expression for Dockerfile installs. It is evaluated inside the image,
# whose parent image can contain a different ZenML version than the client
# building it, and expands to nothing if ZenML isn't installed.
INSTALLED_ZENML_SHELL_REQUIREMENT = (
    "$(pip show zenml 2>/dev/null | sed -n 's/^Version: /zenml==/p')"
)


def get_installed_zenml_requirement() -> Optional[str]:
    """Get a requirement for the ZenML version installed locally.

    Returns:
        `zenml==<version>`, or None if ZenML isn't installed.
    """
    try:
        return f"zenml=={version('zenml')}"
    except PackageNotFoundError:
        return None


def requires_zenml(requirements: Iterable[str]) -> bool:
    """Check whether a list of requirements contains ZenML itself.

    Args:
        requirements: The requirements to check. Lines that aren't valid
            requirements, like comments or installer options, are ignored.

    Returns:
        Whether any of the requirements is for the `zenml` package.
    """
    for requirement in requirements:
        try:
            name = Requirement(requirement).name
        except InvalidRequirement:
            continue
        if canonicalize_name(name) == "zenml":
            return True
    return False
