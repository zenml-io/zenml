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
"""Stacks, stack components, flavors and service connectors.

Credentials never pass through these tools: `zenml_create_stack_component`
refuses configuration keys that look like credentials, and service connectors
are registered by the user in their own terminal.
"""

from __future__ import annotations

from typing import Any

from zenml_mcp import common
from zenml_mcp.call import ZenMLCall
from zenml_mcp.client import (
    ZenMLBadRequest,
    ZenMLNotFound,
    ZenMLRestClient,
)
from zenml_mcp.common import (
    body_of,
    is_uuid,
    iso,
    meta_of,
    read_tool,
    segment,
    write_tool,
)
from zenml_mcp.credentials import (
    component_credentials_refused,
    config_fields,
    credential_like_keys,
    flavor_secret_keys,
)
from zenml_mcp.registry import Tools
from zenml_mcp.resource_spec import COMPONENT_TYPES

_CONFIG_PAGE_SIZE = 10
_LOCAL_ORCHESTRATORS = frozenset({"local", "local_docker"})


def stack_summary(stack: dict[str, Any]) -> dict[str, Any]:
    """A stack as returned to the model: its components by type, flattened.

    Args:
        stack: The hydrated stack, as ZenML answered it.

    Returns:
        The stack's id, name, description, components and `runs_remotely`,
        which is None when the caller can't see an orchestrator.
    """
    components = meta_of(stack).get("components") or {}
    flat = {
        ctype: [
            {
                "id": c.get("id"),
                "name": c.get("name"),
                "flavor": body_of(c).get("flavor_name"),
            }
            for c in items
            if isinstance(c, dict) and not c.get("permission_denied")
        ]
        for ctype, items in components.items()
    }
    orchestrators = flat.get("orchestrator") or []
    runs_remotely = (
        None
        if not orchestrators
        else any(
            o.get("flavor") not in _LOCAL_ORCHESTRATORS for o in orchestrators
        )
    )
    return {
        "id": stack.get("id"),
        "name": stack.get("name"),
        "description": meta_of(stack).get("description"),
        "components": flat,
        "runs_remotely": runs_remotely,
    }


def _connector_type(value: Any) -> str | None:
    """A connector's type name; ZenML sends the full type spec when it has one.

    Args:
        value: The connector's `connector_type`, a name or a type spec.

    Returns:
        The type's name, or None when there is none.
    """
    if isinstance(value, dict):
        return value.get("connector_type")
    return value if isinstance(value, str) else None


def _connector(connector: Any) -> dict[str, Any] | None:
    """A service connector as returned to the model: never its configuration.

    Args:
        connector: The service connector, as ZenML answered it.

    Returns:
        The connector's public fields, or None when the caller can't read it.
    """
    if not isinstance(connector, dict) or connector.get("permission_denied"):
        return None
    body = body_of(connector)
    return {
        "id": connector.get("id"),
        "name": connector.get("name"),
        "connector_type": _connector_type(body.get("connector_type")),
        "auth_method": body.get("auth_method"),
        "resource_types": body.get("resource_types"),
        "resource_id": body.get("resource_id"),
        "expires_at": iso(body.get("expires_at")),
    }


def _flavor(flavor: dict[str, Any]) -> dict[str, Any]:
    body, meta = body_of(flavor), meta_of(flavor)
    return {
        "id": flavor.get("id"),
        "name": flavor.get("name"),
        "display_name": body.get("display_name"),
        "type": body.get("type"),
        "integration": body.get("integration"),
        "is_custom": body.get("is_custom"),
        # Which service connectors the flavor can use: ones that give access
        # to this resource type (and of this connector type, when set).
        "connector_type": meta.get("connector_type"),
        "connector_resource_type": meta.get("connector_resource_type"),
    }


def _check_type(component_type: str) -> str:
    value = component_type.strip()
    if value not in COMPONENT_TYPES:
        raise ZenMLBadRequest(
            f"{component_type!r} is not a stack component type. Use one of: "
            + ", ".join(COMPONENT_TYPES)
            + "."
        )
    return value


async def _find_flavor(
    client: ZenMLRestClient, component_type: str, flavor: str
) -> dict[str, Any]:
    page = await client.get(
        "/flavors",
        params={
            "name": f"equals:{flavor.strip()}",
            "type": component_type,
            "hydrate": True,
            "size": 1,
        },
        what="Finding the flavor",
    )
    items = page.get("items") or []
    if items:
        return items[0]
    available = await client.get(
        "/flavors",
        params={"type": component_type, "sort_by": "asc:name", "size": 200},
        what="Listing the flavors",
    )
    names = [str(f.get("name")) for f in available.get("items") or []]
    raise ZenMLNotFound(
        f"No {component_type} flavor named {flavor!r}. "
        + (
            f"{component_type} flavors on this server: {', '.join(names)}."
            if names
            else "This server has no flavors of that type."
        )
    )


async def _check_connector(
    client: ZenMLRestClient,
    connector_id: str,
    found: dict[str, Any],
    kind: str,
) -> None:
    """Refuse a service connector the flavor cannot use, before anything is created.

    Args:
        client: The caller's ZenML client.
        connector_id: The service connector's ID.
        found: The hydrated flavor.
        kind: The component type, to name the flavor in errors.

    Raises:
        ZenMLBadRequest: If the flavor takes no connector, the caller can't
            read the connector, or it gives the wrong access or type.
    """
    meta = meta_of(found)
    flavor_label = f"{found.get('name')} {kind} flavor"
    resource_type = meta.get("connector_resource_type")
    if not resource_type:
        raise ZenMLBadRequest(
            f"The {flavor_label} can't use a service connector; "
            "create it without connector_id."
        )
    connector = _connector(
        await client.get(
            f"/service_connectors/{segment(connector_id)}",
            params={"expand_secrets": False},
            what="Reading the service connector",
        )
    )
    if connector is None:
        raise ZenMLBadRequest("You can't read that service connector.")
    if resource_type not in (connector.get("resource_types") or []):
        raise ZenMLBadRequest(
            f"Service connector {connector['name']!r} doesn't give access "
            f"to {resource_type} resources, which the {flavor_label} needs."
        )
    wanted = meta.get("connector_type")
    if wanted and connector.get("connector_type") != wanted:
        raise ZenMLBadRequest(
            f"The {flavor_label} needs a {wanted} service connector; "
            f"{connector['name']!r} is a {connector.get('connector_type')} one."
        )


async def _stack_url(client: ZenMLRestClient, stack_id: Any) -> str:
    # The dashboard has no stack page: Pro links the filtered stack list,
    # open source the list (as zenml.utils.dashboard_utils.get_stack_url).
    info = await common.server_info(client)
    suffix = f"?id={stack_id}" if info.is_pro else ""
    return f"{info.dashboard_url}/stacks{suffix}"


def register(tools: Tools) -> None:
    """Register the stack, component, flavor and service connector tools.

    Args:
        tools: The registry the tools are added to.
    """

    @read_tool(tools, "List stacks")
    async def zenml_list_stacks(
        call: ZenMLCall,
        name_contains: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> dict[str, Any]:
        """List stacks (where pipelines run) with their components and whether they run remotely."""  # noqa: DOC101, DOC103, DOC201
        return await common.list_page(
            call.client,
            "/stacks",
            page=page,
            size=size,
            what="Listing stacks",
            item=stack_summary,
            name=f"contains:{name_contains}" if name_contains else None,
            hydrate=True,
            sort_by="asc:name",
        )

    @read_tool(tools, "Get a stack")
    async def zenml_get_stack(call: ZenMLCall, stack: str) -> dict[str, Any]:
        """Get one stack by name or ID: its orchestrator, artifact store, container registry and other components."""  # noqa: DOC101, DOC103, DOC201
        data = await common.by_name_or_id(
            call.client,
            "/stacks",
            stack,
            noun="stack",
            missing=f"No stack named {stack!r}.",
            hydrate=True,
            id_params={"hydrate": True},
        )
        return stack_summary(data)

    @read_tool(tools, "List stack components")
    async def zenml_list_stack_components(
        call: ZenMLCall,
        component_type: str | None = None,
        flavor: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> dict[str, Any]:
        """List stack components such as orchestrators, artifact stores and container registries.

        `component_type` is a ZenML component type, e.g. orchestrator,
        artifact_store, container_registry, step_operator, experiment_tracker.
        """  # noqa: DOC101, DOC103, DOC201
        return await common.list_page(
            call.client,
            "/components",
            page=page,
            size=size,
            what="Listing stack components",
            item=lambda c: {
                "id": c.get("id"),
                "name": c.get("name"),
                "type": body_of(c).get("type"),
                "flavor": body_of(c).get("flavor_name"),
                "integration": body_of(c).get("integration"),
            },
            type=component_type,
            flavor=flavor,
            sort_by="asc:name",
        )

    @read_tool(tools, "List service connectors")
    async def zenml_list_service_connectors(
        call: ZenMLCall,
        connector_type: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> dict[str, Any]:
        """List service connectors (how ZenML authenticates to clouds and clusters). Never returns credentials."""  # noqa: DOC101, DOC103, DOC201
        return await common.list_page(
            call.client,
            "/service_connectors",
            page=page,
            size=size,
            what="Listing service connectors",
            item=_connector,
            connector_type=connector_type,
            expand_secrets=False,
            sort_by="asc:name",
        )

    @read_tool(tools, "List stack component flavors")
    async def zenml_list_flavors(
        call: ZenMLCall,
        component_type: str | None = None,
        name: str | None = None,
        integration: str | None = None,
        include_config: bool = False,
        page: int = 1,
        size: int = 50,
    ) -> dict[str, Any]:
        """List stack component flavors: the implementations a component can use (orchestrator flavors local, kubernetes, sagemaker, vertex…; artifact store flavors local, s3, gcp…).

        Filters: `component_type` (orchestrator, artifact_store,
        container_registry, step_operator, experiment_tracker, …), the exact
        flavor `name`, and `integration`. With `include_config`, each flavor
        lists its configuration fields, required first (at most 10 flavors
        per page, so filter by `name` when you can); fields marked
        `sensitive` are credentials that come from a service connector, never
        through zenml_create_stack_component. `connector_resource_type` says
        which service connectors a flavor can use.
        """  # noqa: DOC101, DOC103, DOC201

        def item(flavor: dict[str, Any]) -> dict[str, Any]:
            shaped = _flavor(flavor)
            if include_config:
                shaped["config_fields"] = config_fields(
                    meta_of(flavor).get("config_schema")
                )
                shaped["docs_url"] = meta_of(flavor).get("docs_url")
            return shaped

        return await common.list_page(
            call.client,
            "/flavors",
            page=page,
            size=size,
            what="Listing flavors",
            item=item,
            # Configuration schemas are large: keep pages small for the model.
            cap=_CONFIG_PAGE_SIZE if include_config else None,
            type=_check_type(component_type) if component_type else None,
            name=f"equals:{name.strip()}" if name else None,
            integration=f"equals:{integration.strip()}"
            if integration
            else None,
            hydrate=True,
            sort_by="asc:name",
        )

    @write_tool(tools, "Create a stack component", destructive=False)
    async def zenml_create_stack_component(
        call: ZenMLCall,
        component_type: str,
        flavor: str,
        name: str,
        configuration: dict[str, Any] | None = None,
        connector_id: str | None = None,
    ) -> dict[str, Any]:
        """Register a stack component, such as an orchestrator, artifact store or container registry, to use in a stack.

        `configuration` takes non-secret settings only (paths, URIs, regions,
        namespaces; zenml_list_flavors with include_config lists them). Keys
        that look like credentials are refused. To give the component access
        to a cloud, the user registers a service connector in their own
        terminal (for example `zenml service-connector register my-aws --type
        aws --auto-configure`); pass its ID as `connector_id`. Then create the
        stack with zenml_create_stack.
        """  # noqa: DOC101, DOC103, DOC201, DOC501, DOC503
        component_type = _check_type(component_type)
        config = configuration or {}
        # Before anything leaves this process: a secret never reaches ZenML.
        secret_keys = credential_like_keys(config)
        if secret_keys:
            raise component_credentials_refused(secret_keys)
        if not name.strip():
            raise ZenMLBadRequest("Give the stack component a name.")
        if connector_id is not None and not is_uuid(connector_id):
            raise ZenMLBadRequest(
                "connector_id must be a service connector ID (a UUID); "
                "zenml_list_service_connectors lists them."
            )
        client = call.client
        found = await _find_flavor(client, component_type, flavor)
        schema_secrets = flavor_secret_keys(found, config)
        if schema_secrets:
            raise component_credentials_refused(schema_secrets)
        if connector_id:
            await _check_connector(client, connector_id, found, component_type)
        body: dict[str, Any] = {
            "name": name.strip(),
            "type": component_type,
            "flavor": found.get("name"),
            "configuration": config,
        }
        if connector_id:
            body["connector"] = connector_id.strip()
        created = await client.write(
            "POST",
            "/components",
            json=body,
            what="Creating the stack component",
        )
        linked = _connector(meta_of(created).get("connector"))
        return {
            "outcome": "created",
            "component": {
                "id": created.get("id"),
                "name": created.get("name"),
                "type": body_of(created).get("type"),
                "flavor": body_of(created).get("flavor_name"),
                "connector": {"id": linked["id"], "name": linked["name"]}
                if linked
                else None,
            },
        }

    @write_tool(tools, "Create a stack", destructive=False)
    async def zenml_create_stack(
        call: ZenMLCall,
        name: str,
        components: dict[str, str],
        description: str | None = None,
    ) -> dict[str, Any]:
        """Create a stack from existing stack components.

        `components` maps a component type (orchestrator, artifact_store,
        container_registry, step_operator, experiment_tracker, …) to a stack
        component ID; an orchestrator and an artifact store are required.
        Create new components first with zenml_create_stack_component, or find
        existing ones with zenml_list_stack_components.
        """  # noqa: DOC101, DOC103, DOC201, DOC501, DOC503
        if not name.strip():
            raise ZenMLBadRequest("Give the stack a name.")
        by_type: dict[str, list[str]] = {}
        for component_type, component_id in components.items():
            checked = _check_type(component_type)
            if not is_uuid(component_id):
                raise ZenMLBadRequest(
                    f"The {checked} must be a stack component ID (a UUID), not "
                    f"{component_id!r}; zenml_list_stack_components lists them."
                )
            by_type[checked] = [component_id.strip()]
        missing = [
            t for t in ("orchestrator", "artifact_store") if t not in by_type
        ]
        if missing:
            raise ZenMLBadRequest(
                "A stack needs an orchestrator and an artifact store; missing: "
                + ", ".join(missing)
                + "."
            )
        client = call.client
        created = await client.write(
            "POST",
            "/stacks",
            json={
                "name": name.strip(),
                "description": description or "",
                "components": by_type,
            },
            what="Creating the stack",
        )
        if not meta_of(created).get("components"):
            created = await client.get(
                f"/stacks/{segment(created['id'])}",
                params={"hydrate": True},
                what="Reading the new stack",
            )
        return {
            "outcome": "created",
            "stack": {
                **stack_summary(created),
                "dashboard_url": await _stack_url(client, created.get("id")),
            },
        }
