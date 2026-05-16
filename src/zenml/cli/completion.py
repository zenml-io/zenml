#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Shell completion helpers for the ZenML CLI."""

import contextlib
import os
import sys
from typing import Any, Callable, Iterable, List

import click

from zenml.client import Client
from zenml.enums import StackComponentType
from zenml.logger import get_logger

logger = get_logger(__name__)

_COMPLETION_SIZE = 100
_DISABLE_DYNAMIC_COMPLETION_ENV = "ZENML_CLI_DISABLE_DYNAMIC_COMPLETION"

ShellCompleteCallback = Callable[
    [click.Context, click.Parameter, str], List[str]
]


def _dynamic_completion_disabled() -> bool:
    """Check whether dynamic completions are disabled by environment."""
    value = os.getenv(_DISABLE_DYNAMIC_COMPLETION_ENV, "")
    return value.lower() in {"1", "true", "yes", "on"}


def _completion_filter(incomplete: str) -> str:
    """Return the server-side name filter for a completion prefix."""
    return f"startswith:{incomplete}" if incomplete else ""


def _names_from_models(models: Iterable[Any]) -> List[str]:
    """Extract names from ZenML response models."""
    names = {
        model.name
        for model in models
        if isinstance(getattr(model, "name", None), str)
    }
    return sorted(names)


def _filter_names(names: Iterable[str], incomplete: str) -> List[str]:
    """Filter and bound completion names by prefix."""
    return sorted({name for name in names if name.startswith(incomplete)})[
        :_COMPLETION_SIZE
    ]


def _query_names(
    query: Callable[[Client, str], Iterable[Any]], incomplete: str
) -> List[str]:
    """Run a best-effort dynamic completion query."""
    if _dynamic_completion_disabled():
        return []

    try:
        with contextlib.redirect_stdout(sys.stderr):
            return _filter_names(
                _names_from_models(query(Client(), incomplete)),
                incomplete,
            )
    except Exception as exc:
        logger.debug("Dynamic shell completion failed: %s", exc)
        return []


def _query_values(
    query: Callable[[Client], Iterable[str]], incomplete: str
) -> List[str]:
    """Run a best-effort dynamic value completion query."""
    if _dynamic_completion_disabled():
        return []

    try:
        with contextlib.redirect_stdout(sys.stderr):
            return _filter_names(query(Client()), incomplete)
    except Exception as exc:
        logger.debug("Dynamic shell completion failed: %s", exc)
        return []


def complete_stack_names(
    ctx: click.Context, param: click.Parameter, incomplete: str
) -> List[str]:
    """Complete existing stack names."""
    return _query_names(
        lambda client, prefix: client.list_stacks(
            name=_completion_filter(prefix),
            size=_COMPLETION_SIZE,
            hydrate=False,
        ),
        incomplete,
    )


def complete_stack_component_names(
    component_type: StackComponentType,
) -> ShellCompleteCallback:
    """Complete existing stack component names for one component type."""

    def _complete(
        ctx: click.Context, param: click.Parameter, incomplete: str
    ) -> List[str]:
        return _query_names(
            lambda client, prefix: client.list_stack_components(
                type=component_type,
                name=_completion_filter(prefix),
                size=_COMPLETION_SIZE,
                hydrate=False,
            ),
            incomplete,
        )

    return _complete


def complete_flavor_names(
    component_type: StackComponentType,
) -> ShellCompleteCallback:
    """Complete registered flavor names for one stack component type."""

    def _complete(
        ctx: click.Context, param: click.Parameter, incomplete: str
    ) -> List[str]:
        return _query_names(
            lambda client, prefix: client.list_flavors(
                type=component_type,
                name=_completion_filter(prefix),
                size=_COMPLETION_SIZE,
                hydrate=False,
            ),
            incomplete,
        )

    return _complete


def complete_service_connector_names(
    ctx: click.Context, param: click.Parameter, incomplete: str
) -> List[str]:
    """Complete existing service connector names."""
    return _query_names(
        lambda client, prefix: client.list_service_connectors(
            name=_completion_filter(prefix),
            size=_COMPLETION_SIZE,
            hydrate=False,
            expand_secrets=False,
        ),
        incomplete,
    )


def complete_secret_names(
    ctx: click.Context, param: click.Parameter, incomplete: str
) -> List[str]:
    """Complete existing secret names without hydrating secret values."""
    return _query_names(
        lambda client, prefix: client.list_secrets(
            name=_completion_filter(prefix),
            size=_COMPLETION_SIZE,
            hydrate=False,
        ),
        incomplete,
    )


def complete_service_connector_types(
    ctx: click.Context, param: click.Parameter, incomplete: str
) -> List[str]:
    """Complete service connector type identifiers."""
    return _query_values(
        lambda client: (
            connector_type.connector_type
            for connector_type in client.list_service_connector_types()
        ),
        incomplete,
    )


def complete_service_connector_resource_types(
    ctx: click.Context, param: click.Parameter, incomplete: str
) -> List[str]:
    """Complete service connector resource type identifiers from metadata."""
    connector_type = ctx.params.get("connector_type") or ctx.params.get("type")

    def _resource_types(client: Client) -> Iterable[str]:
        connector_types = client.list_service_connector_types(
            connector_type=connector_type
        )
        return (
            resource_type.resource_type
            for connector_type_model in connector_types
            for resource_type in connector_type_model.resource_types
        )

    return _query_values(_resource_types, incomplete)


def complete_service_connector_auth_methods(
    ctx: click.Context, param: click.Parameter, incomplete: str
) -> List[str]:
    """Complete service connector auth method identifiers from metadata."""
    connector_type = ctx.params.get("connector_type") or ctx.params.get("type")

    def _auth_methods(client: Client) -> Iterable[str]:
        connector_types = client.list_service_connector_types(
            connector_type=connector_type
        )
        return (
            auth_method
            for connector_type_model in connector_types
            for auth_method in connector_type_model.auth_method_dict
        )

    return _query_values(_auth_methods, incomplete)
