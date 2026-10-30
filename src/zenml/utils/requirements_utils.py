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
# that are already installed. Installing other packages can therefore upgrade
# `opentelemetry-api` past the version that the installed `opentelemetry-sdk`
# requires, e.g. through a newer `fastapi`, after which the SDK fails to
# import. Installs pass the installed versions of these packages as
# constraints to prevent that.
OPENTELEMETRY_PACKAGES = ("opentelemetry-api", "opentelemetry-sdk")
OPENTELEMETRY_CONSTRAINTS_FILE_NAME = ".zenml_opentelemetry_constraints"


def get_opentelemetry_constraints() -> List[str]:
    """Get the installed OpenTelemetry versions as constraints.

    Use this for installs into the current environment. For installs into a
    Docker image, use `get_opentelemetry_constraints_dockerfile_line`.

    Returns:
        A `<package>==<version>` constraint for each installed package of
        `OPENTELEMETRY_PACKAGES`.
    """
    constraints = []
    for package in OPENTELEMETRY_PACKAGES:
        try:
            constraints.append(f"{package}=={version(package)}")
        except PackageNotFoundError:
            continue
    return constraints


def get_opentelemetry_constraints_dockerfile_line() -> str:
    """Get a Dockerfile line that writes the image's OpenTelemetry constraints.

    The versions are read inside the image, because its parent image can
    contain a different ZenML (and therefore OpenTelemetry) version than the
    client that builds it.

    Returns:
        A `RUN` line that writes the constraints for the installed packages of
        `OPENTELEMETRY_PACKAGES` to `OPENTELEMETRY_CONSTRAINTS_FILE_NAME`.
    """
    packages = "|".join(OPENTELEMETRY_PACKAGES)
    # `grep` fails if none of the packages are installed, which is fine.
    return (
        f"RUN pip list --format=freeze | grep -iE '^({packages})==' "
        f"> {OPENTELEMETRY_CONSTRAINTS_FILE_NAME} || true"
    )


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
