#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.

#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:

#       https://www.apache.org/licenses/LICENSE-2.0

#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Functionality to handle interaction with the mlstacks package."""

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

import pkg_resources

from zenml.cli import utils as cli_utils
from zenml.client import Client
from zenml.constants import (
    NOT_INSTALLED_MESSAGE,
    STACK_RECIPE_PACKAGE_NAME,
)


def stack_exists(stack_name: str) -> bool:
    """Checks whether a stack with that name exists or not.

    Args:
        stack_name: The name of the stack to check for.

    Returns:
        A boolean indicating whether the stack exists or not.
    """
    try:
        Client().get_stack(
            name_id_or_prefix=stack_name, allow_name_prefix_match=False
        )
    except KeyError:
        return False
    return True


def verify_mlstacks_installation() -> None:
    """Checks if the `mlstacks` package is installed."""
    try:
        import mlstacks  # noqa: F401
    except ImportError:
        cli_utils.error(NOT_INSTALLED_MESSAGE)


def get_mlstacks_version() -> Optional[str]:
    """Gets the version of mlstacks locally installed.

    Raises:
        pkg_resources.DistributionNotFound: If mlstacks is not installed.
    """
    try:
        return pkg_resources.get_distribution(
            STACK_RECIPE_PACKAGE_NAME
        ).version
    except pkg_resources.DistributionNotFound:
        return


def _get_component_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts component parameters from raw Click CLI params.

    Args:
        params: Raw Click CLI params.

    Returns:
        A dictionary of component parameters.
    """
    component_params = {}
    for key, value in params.items():
        if key.startswith("component_"):
            component_params[key.replace("component_", "")] = value
    return component_params


def convert_click_params_to_mlstacks_primitives(
    params: Dict[str, Any]
) -> Tuple["Stack", List["Component"]]:
    """Converts raw Click CLI params to mlstacks primitives.

    Args:
        params: Raw Click CLI params.

    Returns:
        A tuple of Stack and List[Component] objects.
    """
    verify_mlstacks_installation()
    from mlstacks.models import Component, Stack

    tags = (
        dict(tag.split("=") for tag in params["tags"])
        if params["tags"]
        else {}
    )
    extra_config = (
        dict(config.split("=") for config in params["extra_config"])
        if params["extra_config"]
        else {}
    )

    stack = Stack(
        spec_version=1,
        spec_type="stack",
        name=params["stack_name"],
        provider=params["provider"],
        default_region=params["region"],
        default_tags=tags,
        components=[],
    )
    components = []
    for component in _get_component_params(params):
        components.append(
            Component(
                name=component,
                provider=params["provider"],
                default_region=params["region"],
                default_tags=tags,
                extra_config=extra_config,
                **_get_component_params(params[component]),
            )
        )

    return stack, components
