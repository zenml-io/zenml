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

from typing import TYPE_CHECKING, List, Set, Tuple

from zenml.integrations.utils import get_integration_for_module

if TYPE_CHECKING:
    from zenml.models import ComponentResponse, StackResponse


def get_requirements_for_stack(
    stack: "StackResponse",
) -> Tuple[List[str], List[str]]:
    """Get requirements for a stack model.

    Args:
        stack: The stack for which to get the requirements.

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
        ) = get_requirements_for_component(component=component)
        pypi_requirements = pypi_requirements.union(
            component_pypi_requirements
        )
        apt_packages = apt_packages.union(component_apt_packages)

    return sorted(pypi_requirements), sorted(apt_packages)


def get_requirements_for_component(
    component: "ComponentResponse",
) -> Tuple[List[str], List[str]]:
    """Get requirements for a component model.

    Args:
        component: The component for which to get the requirements.

    Returns:
        Tuple of PyPI and APT requirements of the component.
    """
    integration = get_integration_for_module(
        module_name=component.flavor.source
    )

    if integration:
        return integration.get_requirements(), integration.APT_PACKAGES
    else:
        return [], []
