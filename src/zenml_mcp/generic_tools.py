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
"""The seven generic tools, for every catalogued type.

Describe, list, get, create, update, delete and action, as mcp-zenml defines
them (commit 3de0643). Reads are built in `resources.py`, writes in
`resource_writes.py` and actions in `resource_actions.py`.
"""

from __future__ import annotations

from typing import Any, cast

from zenml_mcp.call import ZenMLCall
from zenml_mcp.common import read_tool, write_tool
from zenml_mcp.credentials import secret_writes
from zenml_mcp.registry import Tools
from zenml_mcp.resource_actions import act
from zenml_mcp.resource_catalog import get_resource_spec
from zenml_mcp.resource_writes import mutate
from zenml_mcp.resources import (
    catalog,
    get_resource,
    list_resources,
)

# mcp-zenml's description of `zenml_describe_resources`, verbatim.
_DESCRIBE_RESOURCES = """Discover supported generic ZenML resources or one operation schema.

    With no arguments this returns a short catalog. Pass a canonical singular
    resource type to inspect its operations, and add an operation name for its
    bounded input schema and a small example.
    """


# mcp-zenml's description of `zenml_list_resources`, verbatim.
_LIST_RESOURCES = """List one allowlisted ZenML resource type with validated filters.

    Use ``zenml_describe_resources(resource_type, "list")`` to discover the
    accepted filters. Page sizes are capped at 200. Project-scoped reads use
    ``project_id`` when supplied and otherwise report the active project used.
    """


# mcp-zenml's description of `zenml_get_resource`, verbatim.
_GET_RESOURCE = """Get one allowlisted ZenML resource by its identifier.

    Artifact versions, model versions, and run steps require their parent
    identifier. Stack components require their fixed component type.
    """


# mcp-zenml's description of `zenml_create_resource`, verbatim.
_CREATE_RESOURCE = """Create one allowlisted ZenML resource with a strict typed payload.

    Inspect ``zenml_describe_resources(resource_type, "create")`` first.
    Project-scoped creates require an exact project UUID and never change the
    client's active project.
    """


# mcp-zenml's description of `zenml_update_resource`, verbatim.
_UPDATE_RESOURCE = """Update one exact UUID through an allowlisted operation-specific payload."""


_DELETE_RESOURCE = """Delete or archive one exact UUID using bounded destructive options.

    An artifact version's `data_deletion` is "not confirmed" when you asked to
    delete its data: the server's answer does not say what it removed from the
    artifact store."""


# mcp-zenml's description of `zenml_action_resource`, verbatim.
_ACTION_RESOURCE = """Run one finite ZenML lifecycle or relation action.

    Inspect ``zenml_describe_resources(resource_type, "action")`` for the exact
    action names and payload schema. Every identifier must be an exact UUID.
    Actions may have effects outside the ZenML server and are never retried.
    """


# Where a secret page may put what it asks for (`*` is any one key).
_SIGNING_SECRET = ("payload", "secret")
_CONFIGURATION = ("payload", "configuration", "*")


def register(tools: Tools) -> None:
    """Register the generic resource tools.

    Args:
        tools: Where the tools are registered.
    """

    @read_tool(
        tools, None, description=_DESCRIBE_RESOURCES, needs_server=False
    )
    async def zenml_describe_resources(
        call: ZenMLCall,
        resource_type: str | None = None,
        operation: str | None = None,
    ) -> dict[str, Any]:
        return catalog(resource_type, operation, read_only=call.read_only)

    @read_tool(tools, None, description=_LIST_RESOURCES)
    async def zenml_list_resources(
        call: ZenMLCall,
        resource_type: str,
        filters: dict[str, Any] | None = None,
        project_id: str | None = None,
        page: int = 1,
        size: int | None = None,
    ) -> dict[str, Any]:
        spec = get_resource_spec(resource_type)
        return await list_resources(
            call.client,
            spec,
            filters=filters,
            project_id=project_id,
            page=page,
            size=size,
        )

    @read_tool(tools, None, description=_GET_RESOURCE)
    async def zenml_get_resource(
        call: ZenMLCall,
        resource_type: str,
        resource_id: str,
        project_id: str | None = None,
        artifact_id: str | None = None,
        model_id: str | None = None,
        pipeline_run_id: str | None = None,
        component_type: str | None = None,
        hydrate: bool | None = None,
    ) -> dict[str, Any]:
        spec = get_resource_spec(resource_type)
        return await get_resource(
            call.client,
            spec,
            resource_id,
            project_id=project_id,
            parent_ids={
                "artifact_id": artifact_id,
                "model_id": model_id,
                "pipeline_run_id": pipeline_run_id,
            },
            component_type=component_type,
            hydrate=hydrate,
        )

    @write_tool(
        tools,
        None,
        destructive=False,
        open_world=True,
        description=_CREATE_RESOURCE,
        secret_writes=secret_writes(
            "create",
            {
                ("webhook", "create"): _SIGNING_SECRET,
                ("service_connector", "create"): _CONFIGURATION,
            },
        ),
    )
    async def zenml_create_resource(
        call: ZenMLCall,
        resource_type: str,
        payload: dict[str, Any] | None = None,
        project_id: str | None = None,
        model_id: str | None = None,
    ) -> dict[str, Any]:
        return await mutate(
            call,
            resource_type,
            "create",
            payload=payload,
            project_id=project_id,
            model_id=model_id,
        )

    @write_tool(
        tools,
        None,
        destructive=False,
        open_world=True,
        description=_UPDATE_RESOURCE,
        secret_writes=secret_writes(
            "update", {("service_connector", "update"): _CONFIGURATION}
        ),
    )
    async def zenml_update_resource(
        call: ZenMLCall,
        resource_type: str,
        resource_id: str,
        payload: dict[str, Any] | None = None,
        project_id: str | None = None,
        artifact_id: str | None = None,
        model_id: str | None = None,
        component_type: str | None = None,
    ) -> dict[str, Any]:
        return await mutate(
            call,
            resource_type,
            "update",
            resource_id=resource_id,
            payload=payload,
            project_id=project_id,
            artifact_id=artifact_id,
            model_id=model_id,
            component_type=component_type,
        )

    @write_tool(
        tools,
        None,
        destructive=True,
        open_world=True,
        description=_DELETE_RESOURCE,
    )
    async def zenml_delete_resource(
        call: ZenMLCall,
        resource_type: str,
        resource_id: str,
        payload: dict[str, Any] | None = None,
        project_id: str | None = None,
        artifact_id: str | None = None,
        model_id: str | None = None,
        component_type: str | None = None,
    ) -> dict[str, Any]:
        return await mutate(
            call,
            resource_type,
            "delete",
            resource_id=resource_id,
            payload=payload,
            project_id=project_id,
            artifact_id=artifact_id,
            model_id=model_id,
            component_type=component_type,
        )

    @write_tool(
        tools,
        None,
        destructive=True,
        open_world=True,
        description=_ACTION_RESOURCE,
        secret_writes=secret_writes(
            "action", {("webhook", "rotate_secret"): _SIGNING_SECRET}
        ),
    )
    async def zenml_action_resource(
        call: ZenMLCall,
        resource_type: str,
        action: str,
        resource_id: str,
        payload: dict[str, Any] | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        # A lost answer is a `CallToolResult`, which the SDK passes through.
        return cast(
            dict[str, Any],
            await act(
                call, resource_type, action, resource_id, payload, project_id
            ),
        )
