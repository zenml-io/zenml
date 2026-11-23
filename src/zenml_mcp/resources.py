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
"""The generic resource core.

It holds how every catalogued type is described, listed, found and written.

Ported from mcp-zenml's `zenml_resource_dispatch.py` (commit 3de0643). That
server calls the ZenML SDK. This one sends the REST request the SDK would
send, as the calling user, from each type's record in `resource_catalog.py`:
its route, the query parameters the SDK adds on its own, and the way the SDK
finds one entity by id, name or prefix.

What `zenml_describe_resources` answers (`catalog`: the catalog, one type, or
the input schema and an example of one operation) is ported from mcp-zenml's
`describe_resources` (commit 3de0643).
"""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal, TypeVar

from mcp.types import CallToolResult

from zenml_mcp import common
from zenml_mcp.call import Asked
from zenml_mcp.client import (
    ZenMLBadRequest,
    ZenMLNotFound,
    ZenMLOutcomeUnknown,
    ZenMLRestClient,
    ZenMLUnavailable,
    page_of,
)
from zenml_mcp.common import (
    canonical_uuid,
    default_project_id,
    segment,
    unknown_outcome,
    utc_naive,
)
from zenml_mcp.credentials import redact
from zenml_mcp.resource_catalog import (
    RESOURCE_REGISTRY,
    get_resource_spec,
)
from zenml_mcp.resource_spec import (
    COMPONENT_TYPES,
    DATETIME_FILTERS,
    MAX_PAGE_SIZE,
    MODEL_STAGES,
    Lookup,
    MutationSpec,
    ResourceSpec,
    matches_schema,
    validate_filter_value,
    validate_mutation_payload,
)

T = TypeVar("T")

# The SDK sends its own default page size with every search. A server can
# configure a different default, so leaving it out would not ask for the same.
SDK_PAGE_SIZE = 20

_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ISO_DT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$"
)
_SPACE_FRAC_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\.\d+$")
_RANGE_RE = re.compile(r"^range:(?P<lower>.+?)\.\.(?P<upper>.+)$")
_KNOWN_OPS = frozenset(
    {
        "equals",
        "notequals",
        "contains",
        "startswith",
        "endswith",
        "oneof",
        "notoneof",
        "gte",
        "gt",
        "lte",
        "lt",
        "in",
    }
)


def _parse_iso_to_zenml(value: str) -> str | None:
    try:
        return utc_naive(value).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return None


def _normalize_datetime_token(value: str, *, upper_bound: bool) -> str:
    value = value.strip()
    if _ISO_DT_RE.match(value):
        parsed = _parse_iso_to_zenml(value)
        if parsed:
            return parsed
    fractional = _SPACE_FRAC_RE.match(value)
    if fractional:
        return fractional.group(1)
    if _DATE_ONLY_RE.match(value):
        return f"{value} {'23:59:59' if upper_bound else '00:00:00'}"
    return value


def normalize_datetime_filter(value: str) -> str:
    """Rewrite ISO-8601, date-only and `range:` inputs into ZenML's format.

    Args:
        value: A datetime filter, with or without an operator.

    Returns:
        The filter in ZenML's format.
    """
    raw = value.strip()
    if not raw:
        return value
    range_match = _RANGE_RE.match(raw)
    if range_match:
        lower = _normalize_datetime_token(
            range_match.group("lower"), upper_bound=False
        )
        upper = _normalize_datetime_token(
            range_match.group("upper"), upper_bound=True
        )
        return f"in:{lower},{upper}"
    head, separator, tail = raw.partition(":")
    operation, operand = (
        (head, tail) if separator and head in _KNOWN_OPS else (None, raw)
    )
    if operation == "in" and "," in operand:
        lower, upper = operand.split(",", 1)
        return (
            f"in:{_normalize_datetime_token(lower, upper_bound=False)},"
            f"{_normalize_datetime_token(upper, upper_bound=True)}"
        )
    normalized = _normalize_datetime_token(
        operand, upper_bound=operation in {"lte", "lt"}
    )
    return f"{operation}:{normalized}" if operation else normalized


def _validate_filter_expression(value: Any) -> None:
    if not isinstance(value, str):
        return
    operation, separator, operand = value.partition(":")
    if not separator or operation not in {"oneof", "notoneof"}:
        return
    try:
        decoded = json.loads(operand)
    except json.JSONDecodeError:
        decoded = None
    if not isinstance(decoded, list):
        raise ZenMLBadRequest(
            'List filters require a JSON array, for example oneof:["running","error"].'
        )


def _has_filter_operator(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    operation, separator, _ = value.partition(":")
    return bool(separator and operation in _KNOWN_OPS)


_SENSITIVE_KEY_PARTS = frozenset(
    {
        "accesskey",
        "apikey",
        "authkey",
        "credential",
        "databaseurl",
        "password",
        "privatekey",
        "refreshtoken",
        "secret",
        "signingkey",
        "token",
    }
)
_OPAQUE_SENSITIVE_FIELDS = frozenset(
    {
        "config",
        "configuration",
        "environment",
        "environmentvariables",
        "parameters",
        "secrets",
        "settings",
        "values",
    }
)


def _is_omitted(key: str, resource_type: str) -> bool:
    spec = RESOURCE_REGISTRY.get(resource_type)
    lowered = key.lower()
    collapsed = re.sub(r"[^a-z0-9]", "", lowered)
    return (
        any(part in collapsed for part in _SENSITIVE_KEY_PARTS)
        or collapsed in _OPAQUE_SENSITIVE_FIELDS
        or collapsed.endswith(
            (
                "config",
                "configuration",
                "environment",
                "parameters",
                "settings",
            )
        )
        or (spec is not None and lowered in spec.omitted_fields)
    )


def _safe_project(value: Any, *, resource_type: str) -> Any:
    """Drop credential keys and opaque configuration containers, at any depth.

    Args:
        value: A value from ZenML's answer.
        resource_type: The type the value belongs to.

    Returns:
        The value without the omitted keys.
    """
    if isinstance(value, Mapping):
        return {
            str(key): _safe_project(child, resource_type=resource_type)
            for key, child in value.items()
            if not _is_omitted(str(key), resource_type)
        }
    if isinstance(value, list):
        return [
            _safe_project(item, resource_type=resource_type) for item in value
        ]
    return value


def projected(value: Any, *, resource_type: str) -> Any:
    """An entity as the generic tools return it.

    It has no credential-like keys and no configuration, environment,
    parameter or settings containers.

    Args:
        value: The entity, or a list of them, as ZenML answered.
        resource_type: The entity's type.

    Returns:
        The projected, redacted entity.
    """
    return redact(_safe_project(value, resource_type=resource_type))


def parses_as(resource_type: str, answer: Any) -> bool:
    """Whether the SDK would parse ZenML's answer as that type's response.

    This goes as far as the fields its model requires: a UUID `id`, and a
    `name` where the model has one. The SDK also checks the types of the rest.

    Args:
        resource_type: The type of the response.
        answer: ZenML's answer.

    Returns:
        Whether the answer has the fields the SDK requires.
    """
    if (
        not isinstance(answer, dict)
        or canonical_uuid(str(answer.get("id"))) is None
    ):
        return False
    spec = RESOURCE_REGISTRY.get(resource_type)
    named = spec is not None and spec.named_response
    return not named or isinstance(answer.get("name"), str)


def _required_uuid(name: str, value: str | None) -> str | None:
    if value is None:
        return None
    parsed = canonical_uuid(value.strip())
    if parsed is None:
        raise ZenMLBadRequest(f"{name} must be a non-empty UUID")
    return parsed


async def _effective_scope(
    client: ZenMLRestClient, spec: ResourceSpec, project_id: str | None
) -> tuple[dict[str, Any], str | None]:
    if spec.scope == "global":
        if project_id is not None:
            raise ZenMLBadRequest(
                f"{spec.resource_type!r} is global and does not accept project_id"
            )
        return {"kind": "global"}, None
    requested = _required_uuid("project_id", project_id)
    if requested is not None:
        return {
            "kind": "project",
            "project_id": requested,
            "source": "requested",
        }, requested
    chosen = await default_project_id(client)
    return {
        "kind": "project",
        "project_id": chosen,
        "source": "active_project",
    }, chosen


def _validated_filters(
    spec: ResourceSpec, filters: Mapping[str, Any] | None
) -> dict[str, Any]:
    supplied = dict(filters or {})
    unsupported = sorted(set(supplied) - set(spec.list_filters))
    if unsupported:
        raise ZenMLBadRequest(
            f"Unsupported filters for {spec.resource_type!r}: "
            f"{', '.join(unsupported)}. "
            f"Allowed filters: {', '.join(spec.list_filters)}"
        )
    missing = [
        f for f in spec.list_required_filters if supplied.get(f) is None
    ]
    if missing:
        raise ZenMLBadRequest(
            f"{spec.resource_type!r} list requires filters: {', '.join(missing)}"
        )
    for key, value in supplied.items():
        validate_filter_value(spec.resource_type, key, value)
        _validate_filter_expression(value)
        if key in DATETIME_FILTERS:
            if isinstance(value, str):
                supplied[key] = normalize_datetime_filter(value)
            elif isinstance(value, list):
                supplied[key] = [
                    normalize_datetime_filter(item) for item in value
                ]
        elif isinstance(value, list) and not any(
            _has_filter_operator(item) for item in value
        ):
            supplied[key] = f"oneof:{json.dumps(value, separators=(',', ':'))}"
        elif isinstance(value, dict):
            supplied[key] = json.dumps(value)
    for name, sent_as in spec.rest.renames.items():
        if supplied.get(name):
            supplied[sent_as] = supplied.pop(name)
    return supplied


def _as_remote(connector_type: Any) -> Any:
    """Mark a connector type as the server's, the way the SDK does.

    Args:
        connector_type: A connector type, or a connector's type name.

    Returns:
        The connector type marked remote, or the value unchanged when it is
        not a full type.
    """
    if isinstance(connector_type, dict):
        return {**connector_type, "local": False, "remote": True}
    return connector_type


def with_remote_connector_type(connector: Any) -> Any:
    """A connector with its type marked as the server's, as the SDK holds it.

    Args:
        connector: The connector as ZenML answered it.

    Returns:
        The connector with its type marked remote.
    """
    body = connector.get("body") if isinstance(connector, dict) else None
    if not isinstance(body, dict):
        return connector
    kind = _as_remote(body.get("connector_type"))
    return {**connector, "body": {**body, "connector_type": kind}}


def _with_connector_type_name(connector: Any) -> Any:
    """A listed connector carries its type's name, not the full type spec.

    Args:
        connector: A connector as ZenML listed it.

    Returns:
        The connector with its type's name in place of its type.
    """
    body = connector.get("body") if isinstance(connector, dict) else None
    if not isinstance(body, dict):
        return connector
    kind = body.get("connector_type")
    if isinstance(kind, dict):
        kind = kind.get("connector_type") or kind.get("name")
    return {**connector, "body": {**body, "connector_type": kind}}


async def list_resources(
    client: ZenMLRestClient,
    spec: ResourceSpec,
    *,
    filters: Mapping[str, Any] | None,
    project_id: str | None,
    page: int,
    size: int | None,
) -> dict[str, Any]:
    """One page of a type's entities, listed the way the SDK lists them.

    Args:
        client: The client of the calling user.
        spec: The type to list.
        filters: The list filters given.
        project_id: The project to list in, or None for the default one.
        page: The page number, from 1.
        size: The page size, or None for the type's default.

    Returns:
        The projected page and its effective scope.

    Raises:
        ZenMLBadRequest: When the page or size is out of range.
    """
    resource_type, rest = spec.resource_type, spec.rest
    size = spec.default_size if size is None else size
    if page < 1:
        raise ZenMLBadRequest(
            "page must be an integer greater than or equal to 1"
        )
    if not 1 <= size <= MAX_PAGE_SIZE:
        raise ZenMLBadRequest(f"size must be between 1 and {MAX_PAGE_SIZE}")
    scope, project = await _effective_scope(client, spec, project_id)
    supplied = _validated_filters(spec, filters)
    what = f"Listing {spec.description.lower()}"
    if spec.non_paginated:
        found = await client.get(rest.route, params=supplied, what=what)
        everything = [_as_remote(item) for item in found]
        start = (page - 1) * size
        items, total = everything[start : start + size], len(everything)
    else:
        found = await client.get(
            rest.route,
            params={
                **rest.list_defaults,
                **rest.always,
                **supplied,
                "project": project,
                "page": page,
                "size": size,
                "hydrate": False,
            },
            what=what,
        )
        items = found.get("items", [])
        if resource_type == "service_connector":
            items = [_with_connector_type_name(item) for item in items]
        total = int(found.get("total", len(items)))
        page = int(found.get("page", found.get("index", page)))
        size = int(found.get("size", found.get("max_size", size)))
    answer = {
        "resource_type": resource_type,
        "items": projected(items, resource_type=resource_type),
        "total": total,
        "page": page,
        "size": size,
        "effective_scope": scope,
    }
    return common.fit_page(answer, page=page, size=size)


async def find_entity(
    client: ZenMLRestClient,
    spec: ResourceSpec,
    resource_id: str,
    *,
    project: str | None,
    hydrate: bool,
    component_type: str | None,
    model_id: str | None,
    name_prefix: bool = True,
) -> Any:
    """One entity, found the way the SDK's get method for its type finds it.

    `name_prefix=False` is the SDK's `allow_name_prefix_match=False`.

    Args:
        client: The client of the calling user.
        spec: The entity's type.
        resource_id: The id, id prefix, name or name prefix to find.
        project: The project to search in.
        hydrate: Whether to read the entity hydrated.
        component_type: The stack component type, for a stack component.
        model_id: The model, for a model version.
        name_prefix: Whether a name prefix may match.

    Returns:
        The entity as ZenML answered it.

    Raises:
        ZenMLNotFound: When an id finds a trigger of another type, or an
            archived one.
    """  # noqa: DOC502
    resource_type, rest = spec.resource_type, spec.rest
    label = resource_type.replace("_", " ")
    what = f"Reading the {label}"

    async def by_id(value: str, **params: Any) -> Any:
        return await client.get(
            f"{rest.route}/{segment(value)}",
            params={**rest.always, **params},
            what=what,
        )

    async def search(**criteria: Any) -> dict[str, Any]:
        return await client.page(
            rest.route,
            params={
                **rest.always,
                "project": project,
                "hydrate": hydrate,
                "size": SDK_PAGE_SIZE,
                **criteria,
            },
            what=what,
        )

    def only(items: list[Any], total: int) -> Any:
        """The single match of a search that found `total` entities.

        Args:
            items: The entities the search answered.
            total: How many entities the search found.

        Returns:
            The single match.

        Raises:
            ZenMLNotFound: When the search found none or several.
        """
        if total == 1 and items:
            return items[0]
        if total <= 1:
            raise ZenMLNotFound(f"No {label} matches {resource_id!r}.")
        raise ZenMLNotFound(
            f"{total} {label}s match {resource_id!r}; use the full id."
        )

    async def by_id_prefix(**criteria: Any) -> Any:
        page = await search(id=f"startswith:{resource_id}", **criteria)
        return only(page["items"], page["total"])

    async def connector_type() -> Any:
        return _as_remote(await by_id(resource_id))

    async def id_only() -> Any:
        return await by_id(
            resource_id,
            hydrate=hydrate and resource_type != "resource_request",
        )

    async def model_version() -> Any:
        if resource_id == "latest":
            newest = (await search(model=model_id, sort_by="desc:number"))[
                "items"
            ][:1]
            return only(newest, len(newest))
        field = "stage" if resource_id in MODEL_STAGES else "name"
        page = await search(model=model_id, **{field: resource_id})
        return only(page["items"], len(page["items"]))

    async def snapshot() -> Any:
        page = await search(name=resource_id, size=1)
        if page["total"] == 0:
            return await by_id_prefix(size=1)
        return only(page["items"], page["total"])

    async def version() -> Any:
        page = await search(
            **rest.list_defaults,
            artifact=resource_id,
            size=1,
            sort_by="desc:created",
        )
        if len(page["items"]) == 1:
            return page["items"][0]
        return await by_id_prefix(**rest.list_defaults)

    async def by_name() -> Any:
        criteria = {**rest.list_defaults, **rest.lookup_overrides}
        if resource_type == "stack_component":
            criteria["scope_type"] = component_type
        exact = await search(name=f"equals:{resource_id}", **criteria)
        if exact["total"] != 0:
            return only(exact["items"], exact["total"])
        matches: dict[Any, Any] = {}
        for by in (
            ("id", "name") if rest.name_prefix and name_prefix else ("id",)
        ):
            page = await search(
                **{by: f"startswith:{resource_id}"}, **criteria
            )
            matches.update({item.get("id"): item for item in page["items"]})
        return only(list(matches.values()), len(matches))

    strategies: dict[Lookup, Callable[[], Awaitable[Any]]] = {
        "connector_type": connector_type,
        "id": id_only,
        "model_version": model_version,
        "build": by_id_prefix,
        "snapshot": snapshot,
        "version": version,
        "name": by_name,
    }
    known_id = canonical_uuid(resource_id)
    if known_id and rest.lookup not in ("connector_type", "id"):
        found = await by_id(known_id, hydrate=hydrate)
        if spec.trigger:
            body = common.body_of(found)
            if (
                body.get("type") != spec.trigger[0]
                or body.get("is_archived") is not False
            ):
                raise ZenMLNotFound(
                    f"No {resource_type} has the id {resource_id!r}."
                )
        return found
    return await strategies[rest.lookup]()


def find_nested_id(value: Any, direct_key: str, nested_key: str) -> str | None:
    """A relation's id, wherever the response nests it.

    Args:
        value: The response, or part of it.
        direct_key: The key that holds the id itself.
        nested_key: The key that holds the related entity.

    Returns:
        The first id found, or None.
    """
    if isinstance(value, Mapping):
        direct = value.get(direct_key)
        if direct is not None:
            return str(direct)
        nested = value.get(nested_key)
        if isinstance(nested, Mapping) and nested.get("id") is not None:
            return str(nested["id"])
        children: Any = value.values()
    elif isinstance(value, list):
        children = value
    else:
        return None
    for child in children:
        found = find_nested_id(child, direct_key, nested_key)
        if found is not None:
            return found
    return None


def find_nested_value(value: Any, key: str) -> Any:
    """A key's first non-null value, wherever the response nests it.

    Args:
        value: The response, or part of it.
        key: The key to look for.

    Returns:
        The first value found, or None.
    """
    if isinstance(value, Mapping):
        if key in value:
            return value[key]
        children: Any = value.values()
    elif isinstance(value, list):
        children = value
    else:
        return None
    for child in children:
        found = find_nested_value(child, key)
        if found is not None:
            return found
    return None


async def find(
    client: ZenMLRestClient,
    resource_type: Literal["pipeline", "stack"],
    name_or_id: str,
    *,
    name_prefix: bool = True,
) -> Any:
    """A hydrated pipeline in the caller's default project, or a stack.

    It is found the way the SDK's get method finds it. Types that need a
    parent or a component type go through `get_resource`, which checks those.

    Args:
        client: The client of the calling user.
        resource_type: The entity's type.
        name_or_id: The id, id prefix, name or name prefix to find.
        name_prefix: Whether a name prefix may match.

    Returns:
        The entity as ZenML answered it.
    """
    spec = get_resource_spec(resource_type)
    _, project = await _effective_scope(client, spec, None)
    return await find_entity(
        client,
        spec,
        name_or_id,
        project=project,
        hydrate=True,
        component_type=None,
        model_id=None,
        name_prefix=name_prefix,
    )


def _checked_identifiers(
    spec: ResourceSpec,
    resource_id: str,
    parent_ids: Mapping[str, str | None],
    component_type: str | None,
) -> dict[str, str | None]:
    """The identifiers a get was given, once known to be the ones it takes.

    Args:
        spec: The type to get.
        resource_id: The entity's identifier.
        parent_ids: The parent ids given, by name.
        component_type: The stack component type given.

    Returns:
        The parent ids and component type, the ids as canonical UUIDs.

    Raises:
        ZenMLBadRequest: When an identifier is empty, missing, not taken by
            the type, or an invalid component type.
    """
    resource_type = spec.resource_type
    spec.operation_spec("get")
    if not resource_id.strip():
        raise ZenMLBadRequest("resource_id must be a non-empty identifier")
    supplied: dict[str, str | None] = {
        **{
            name: _required_uuid(name, value)
            for name, value in parent_ids.items()
        },
        "component_type": component_type,
    }
    missing = [
        name
        for name in spec.get_required
        if name != "resource_id" and supplied.get(name) is None
    ]
    if missing:
        raise ZenMLBadRequest(
            f"{resource_type!r} get requires: {', '.join(missing)}"
        )
    unexpected = sorted(
        name
        for name, value in supplied.items()
        if value is not None and name not in (spec.get_fields or ())
    )
    if unexpected:
        raise ZenMLBadRequest(
            f"Unexpected identifiers for {resource_type!r}: {', '.join(unexpected)}"
        )
    if (
        resource_type == "stack_component"
        and component_type not in COMPONENT_TYPES
    ):
        raise ZenMLBadRequest("Invalid component_type")
    return supplied


async def get_resource(
    client: ZenMLRestClient,
    spec: ResourceSpec,
    resource_id: str,
    *,
    project_id: str | None,
    parent_ids: Mapping[str, str | None],
    component_type: str | None,
    hydrate: bool | None,
) -> dict[str, Any]:
    """One entity, checked to be in its project, parent and component type.

    Args:
        client: The client of the calling user.
        spec: The entity's type.
        resource_id: The id, id prefix, name or name prefix to find.
        project_id: The project to search in, or None for the default one.
        parent_ids: The parent ids given, by name.
        component_type: The stack component type given.
        hydrate: Whether to read the entity hydrated, or None for the
            type's default.

    Returns:
        The projected entity and its effective scope.

    Raises:
        ZenMLNotFound: When the entity is not of the component type, under
            the parent or in the project.
    """
    resource_type = spec.resource_type
    supplied = _checked_identifiers(
        spec, resource_id, parent_ids, component_type
    )
    scope, project = await _effective_scope(client, spec, project_id)
    item = await find_entity(
        client,
        spec,
        resource_id,
        project=project,
        hydrate=resource_type in {"run_step", "tag"}
        if hydrate is None
        else hydrate,
        component_type=component_type,
        model_id=supplied["model_id"],
    )
    if resource_type == "service_connector":
        item = with_remote_connector_type(item)
    if resource_type == "stack_component":
        observed = find_nested_value(item, "type")
        if observed is None or str(observed).lower() != component_type:
            raise ZenMLNotFound(
                "'stack_component' was not found for the supplied component_type"
            )
    if spec.parent:
        direct_key, nested_key = spec.parent
        if (
            find_nested_id(item, direct_key, nested_key)
            != supplied[direct_key]
        ):
            raise ZenMLNotFound(
                f"{resource_type!r} does not belong to the supplied parent"
            )
    if (
        spec.scope == "project"
        and find_nested_id(item, "project_id", "project") != project
    ):
        raise ZenMLNotFound(
            f"{resource_type!r} was not found in the effective project"
        )
    return {
        "resource_type": resource_type,
        "item": projected(item, resource_type=resource_type),
        "effective_scope": scope,
    }


async def validated(read: Awaitable[T]) -> T:
    """A read upstream makes before its own `try`.

    A lost answer there is an error, as upstream raises it, not an unknown
    outcome.

    Args:
        read: The read to await.

    Returns:
        The read's result.

    Raises:
        ZenMLUnavailable: When the read is unavailable or its outcome is
            unknown.
    """
    try:
        return await read
    except (ZenMLUnavailable, ZenMLOutcomeUnknown) as error:
        raise ZenMLUnavailable(error.message, status=error.status) from None


def exact_uuid(name: str, value: Any) -> str:
    """A value that must already be a canonical UUID, in any case.

    Args:
        name: The argument's name, for the error.
        value: The value given.

    Returns:
        The UUID in lower case.

    Raises:
        ZenMLBadRequest: When the value is not an exact UUID.
    """
    if not isinstance(value, str) or canonical_uuid(value) != value.lower():
        raise ZenMLBadRequest(f"{name} must be an exact UUID")
    return value.lower()


@dataclass(frozen=True)
class WriteRequest:
    """One checked write: where it goes and who it is about."""

    client: ZenMLRestClient
    spec: ResourceSpec
    payload: dict[str, Any]
    project: str | None
    target: str | None = None
    artifact_id: str | None = None
    model_id: str | None = None
    component_type: str | None = None
    # With a secret page: the secret fields the page must ask for are
    # collected here, and the write is withheld when any were found.
    asking: list[Asked] | None = None
    # With a secret page: stored secrets a write resends, kept out of its
    # errors.
    resent: list[str] | None = None

    @property
    def route(self) -> str:
        """The type's REST route.

        Returns:
            The route.
        """
        return self.spec.rest.route

    async def read(
        self, resource_type: str, resource_id: str, *, hydrate: bool = True
    ) -> Any:
        """One entity by id, the way the SDK's get method reads it.

        Args:
            resource_type: The entity's type.
            resource_id: The entity's identifier.
            hydrate: Whether to read the entity hydrated.

        Returns:
            The entity as ZenML answered it.
        """
        return await find_entity(
            self.client,
            get_resource_spec(resource_type),
            resource_id,
            project=self.project,
            hydrate=hydrate,
            component_type=None,
            model_id=None,
        )

    async def checked(
        self,
        resource_type: str,
        resource_id: str,
        *,
        scoped: bool = True,
        artifact_id: str | None = None,
        model_id: str | None = None,
        component_type: str | None = None,
    ) -> dict[str, Any]:
        """A related entity, read through the generic get.

        It must exist under this exact id, in the project, under the parent
        and with the type.

        Args:
            resource_type: The entity's type.
            resource_id: The entity's exact UUID.
            scoped: Whether it must be in the request's project.
            artifact_id: The parent artifact, for an artifact version.
            model_id: The parent model, for a model version.
            component_type: The stack component type, for a stack component.

        Returns:
            The projected entity and its effective scope.

        Raises:
            ZenMLNotFound: When the entity found has another id.
        """
        found = await validated(
            get_resource(
                self.client,
                get_resource_spec(resource_type),
                resource_id,
                project_id=self.project if scoped else None,
                parent_ids={
                    "artifact_id": artifact_id,
                    "model_id": model_id,
                    "pipeline_run_id": None,
                },
                component_type=component_type,
                hydrate=None,
            )
        )
        if find_nested_id(found["item"], "id", "id") != resource_id:
            raise ZenMLNotFound(
                f"{resource_type!r} did not resolve to the exact supplied UUID"
            )
        return found

    async def taken(self, name: str, **criteria: Any) -> bool:
        """Whether the SDK's search for a name finds an entity of this type.

        Args:
            name: The name to look for.
            criteria: Further query parameters for the search.

        Returns:
            Whether an entity has that name.
        """
        page = await self.client.get(
            self.route,
            params={
                "name": name,
                **criteria,
                "hydrate": False,
                "size": SDK_PAGE_SIZE,
            },
            what=f"Looking for a {self.spec.resource_type} of that name",
        )
        return bool(page.get("items"))

    async def listed(self, resource_type: str, resource_id: str) -> None:
        """Upstream finds these targets by listing their type with an id filter.

        Args:
            resource_type: The target's type.
            resource_id: The target's exact UUID.

        Raises:
            ZenMLNotFound: When the target is not in the project.
        """
        exact_uuid("target_id", resource_id)
        page = await list_resources(
            self.client,
            get_resource_spec(resource_type),
            filters={"id": resource_id},
            project_id=self.project,
            page=1,
            size=2,
        )
        exact = [
            item
            for item in page_of(page)["items"]
            if find_nested_id(item, "id", "id") == resource_id
        ]
        if len(exact) != 1:
            raise ZenMLNotFound(
                f"{resource_type!r} was not found in the effective project"
            )

    async def default_project(self) -> str:
        """The caller's default project, read through `validated`.

        Returns:
            The project's id.
        """
        return await validated(default_project_id(self.client))

    def outcome(
        self,
        scope: dict[str, Any],
        reconciliation: dict[str, Any],
        **fields: Any,
    ) -> dict[str, Any]:
        """What a write or an action answers.

        The fields go in the order given, between the resource type and the
        scope.

        Args:
            scope: The effective scope.
            reconciliation: The read that shows whether the write applied.
            fields: The answer's own fields.

        Returns:
            The answer.
        """
        return {
            "resource_type": self.spec.resource_type,
            **fields,
            "effective_scope": scope,
            "reconciliation": reconciliation,
        }


def lost_answer(
    tool: str, subject: str, recovery: str, details: dict[str, Any]
) -> CallToolResult:
    """mcp-zenml's answer to a `subject` whose response was lost.

    Args:
        tool: The tool that sent the request.
        subject: What the request was executing.
        recovery: What the caller should do next.
        details: The answer's structured content.

    Returns:
        The unknown-outcome result.
    """
    message = (
        f"The response was lost while executing the {subject} or could not be "
        "decoded; it may have been dispatched, so the outcome is unknown. "
        + recovery
    )
    return unknown_outcome(tool, message, details)


_OUTPUT_PROJECTION = (
    "Credential keys and opaque configuration, environment, parameter, "
    "settings, secret, and value containers are omitted recursively."
)
_WRITES = frozenset({"create", "update", "delete"})


_EXAMPLE_UUID = "00000000-0000-4000-8000-000000000001"


def _example_value(schema: Mapping[str, Any]) -> Any:
    """Build a small concrete value accepted by a registry-owned schema.

    Args:
        schema: The JSON schema.

    Returns:
        An example value.
    """
    if "const" in schema:
        return schema["const"]
    if schema.get("enum"):
        return schema["enum"][0]
    for keyword in ("anyOf", "oneOf"):
        for alternative in schema.get(keyword, ()):
            candidate = _example_value(alternative)
            if matches_schema(candidate, alternative):
                return candidate
    schema_type = schema.get("type")
    if schema_type == "string":
        if schema.get("format") == "uuid":
            return _EXAMPLE_UUID
        if schema.get("format") == "date-time":
            return "2026-01-01T00:00:00Z"
        return "example"
    if schema_type == "boolean":
        return True
    if schema_type in {"integer", "number"}:
        return max(1, schema.get("minimum", 1))
    if schema_type == "array":
        return [_example_value(schema.get("items", {}))]
    if schema_type == "object":
        properties = schema.get("properties", {})
        required = schema.get("required", ())
        if required:
            return {
                field: _example_value(properties[field])
                for field in required
                if field in properties
            }
        if schema.get("additionalProperties") is not False:
            additional = schema.get("additionalProperties", {})
            additional_schema = (
                additional if isinstance(additional, Mapping) else {}
            )
            return {"example": _example_value(additional_schema)}
        return {}
    return "example"


def _update_example_payload(
    spec: ResourceSpec, mutation: MutationSpec
) -> dict[str, Any]:
    if mutation.example_payload is not None:
        return dict(mutation.example_payload)
    for field, schema in mutation.payload_properties.items():
        candidate = {field: _example_value(schema)}
        try:
            validate_mutation_payload(spec, "update", candidate)
        except ZenMLBadRequest:
            continue
        return candidate
    raise ZenMLBadRequest(
        f"Unable to build update example for {spec.resource_type!r}"
    )


def _summary(
    spec: ResourceSpec, read_only: bool, actions: list[str] | None = None
) -> dict[str, Any]:
    """A type as the catalog lists it.

    With `actions`, it is as describing the type answers, which lists them
    after the operations.

    Args:
        spec: The type.
        read_only: Whether writes and actions are left out.
        actions: The type's action names, or None to leave them out.

    Returns:
        The type's summary.
    """
    acts = ["action"] if spec.actions else []
    offered = spec.operations
    writes = bool(acts) or any(operation in _WRITES for operation in offered)
    operations: list[str]
    if read_only:
        operations = [op for op in offered if op not in _WRITES]
    else:
        operations = [*offered, *acts]
    return {
        "resource_type": spec.resource_type,
        "operations": operations,
        **({"actions": actions} if actions is not None else {}),
        "scope": spec.scope,
        "policy": "read_write" if writes and not read_only else "read_only",
        "description": spec.description,
    }


def describe_resources(
    resource_type: str | None = None,
    operation: str | None = None,
    *,
    read_only: bool = False,
) -> dict[str, Any]:
    """Return the bounded catalog or one operation schema.

    It leaves out the writes and actions a type does not offer
    (`not_offered`). `read_only` is upstream's read-only write policy: no
    create, update, delete or action.

    Args:
        resource_type: A catalogued type, or None for the whole catalog.
        operation: One of its operations, or None for the type's summary.
        read_only: Whether writes and actions are disabled.

    Returns:
        The catalog, the type's summary, or the operation's schema and
        example.

    Raises:
        ZenMLBadRequest: When an operation is given without a type, is
            disabled by the read-only policy, or the type has no actions.
    """
    if resource_type is None:
        if operation is not None:
            raise ZenMLBadRequest("operation requires resource_type")
        return {
            "resources": [
                _summary(spec, read_only)
                for spec in RESOURCE_REGISTRY.values()
            ]
        }

    spec = get_resource_spec(resource_type)
    actions = [] if read_only else list(spec.actions.values())
    if operation is None:
        return _summary(spec, read_only, [action.action for action in actions])
    if read_only and operation in {*_WRITES, "action"}:
        raise ZenMLBadRequest(
            f"Operation {operation!r} is disabled by the read-only policy"
        )
    if operation == "action":
        if not actions:
            raise ZenMLBadRequest(
                f"Unsupported operation 'action' for {resource_type!r}"
            )
        return {
            "resource_type": resource_type,
            "operation": "action",
            "scope": "project",
            "resource_scope": spec.scope,
            "scope_note": (
                "project_id selects and verifies the affected resource or relation target; "
                "it does not change the client's active project."
            ),
            "actions": [
                {
                    "action": action.action,
                    "sdk_method": action.sdk_method,
                    "input_schema": action.schema(),
                    "prerequisites": list(action.prerequisites),
                }
                for action in actions
            ],
            "output_projection": (
                f"{_OUTPUT_PROJECTION} A newly issued webhook secret is returned once."
            ),
        }

    operation_spec = spec.operation_spec(operation)
    input_schema = operation_spec.schema()
    example: dict[str, Any] = {"resource_type": resource_type}
    if operation == "list":
        example.update(
            {
                "page": 1,
                "size": spec.default_size,
                "filters": {
                    field: f"<{field}>" for field in spec.list_required_filters
                },
            }
        )
    elif operation == "get":
        example.update(
            {field: f"<{field}>" for field in operation_spec.required_fields}
        )
    elif operation == "update":
        mutation = spec.mutations[operation]
        for field in operation_spec.required_fields:
            example[field] = (
                _update_example_payload(spec, mutation)
                if field == "payload"
                else _example_value(input_schema["properties"][field])
            )
    else:
        for field in operation_spec.required_fields:
            if field == "payload":
                mutation = spec.mutations[operation]
                example[field] = (
                    dict(mutation.example_payload)
                    if mutation.example_payload is not None
                    else {key: f"<{key}>" for key in mutation.required_payload}
                )
            else:
                example[field] = f"<{field}>"
    return {
        "resource_type": resource_type,
        "operation": operation,
        "scope": spec.scope,
        "description": operation_spec.description,
        "input_schema": input_schema,
        "example": example,
        "output_projection": _OUTPUT_PROJECTION,
    }


def catalog(
    resource_type: str | None = None,
    operation: str | None = None,
    *,
    read_only: bool = False,
) -> dict[str, Any]:
    """The catalog, or one operation schema, as this server offers it.

    Args:
        resource_type: A catalogued type, for its operations.
        operation: One of its operations, for its schema.
        read_only: Whether the server offers no write tool, which makes the
            catalog follow upstream's read-only policy.

    Returns:
        The catalog, or the type's operations, or the operation's schema.
    """
    return describe_resources(resource_type, operation, read_only=read_only)
