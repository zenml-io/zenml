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
"""Create, update and delete for catalogued types, behind the generic write tools.

Ported from mcp-zenml's `mutate_resource` (commit 3de0643). That server checks
a request, then calls the ZenML SDK. This one makes the same checks, then
sends the REST requests the SDK's method would send (ZenML 0.97.0,
`client.py`): the reads the SDK uses to find the entity or to merge with it,
and the one write.

Two things differ on purpose. A key that looks like a credential is refused
before any request, and so is a field that a stack component's flavor marks as
a secret, before the write: an update that changes a configuration reads the
flavor for that, which upstream does not. What the SDK checks with Python
classes installed next to it (a flavor's or a code repository's configuration
class) is left to ZenML.
The SDK's active project is the caller's default project here.

The secret writes take their secrets on the secret page: the tool answers
with a link, after the reads a connector write makes to know which secret
attributes to ask for, and a connector write that needs none is sent directly.
The page runs the write as upstream does: a connector's `configuration` and a
webhook's `secret` skip the key check, and a webhook secret ZenML issued is
returned as `issued_secret`. Connector bodies are built in `connectors.py`.
"""

from __future__ import annotations

import copy
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import replace
from typing import Any

from zenml_mcp.call import ZenMLCall, ask_if_sensitive
from zenml_mcp.client import (
    UNREADABLE,
    ZenMLAlreadyExists,
    ZenMLBadRequest,
    ZenMLNotFound,
    ZenMLOutcomeUnknown,
    ZenMLRestError,
    ZenMLUnavailable,
)
from zenml_mcp.common import (
    answer_lost,
    body_of,
    default_project_id,
    field_of,
    meta_of,
    segment,
    utc_naive,
)
from zenml_mcp.connectors import (
    connector_as_the_sdk_holds,
    create_service_connector,
    update_service_connector,
)
from zenml_mcp.credentials import (
    WEBHOOK_SECRET,
    awaiting_user,
    flavor_secret_keys,
    refuse_credentials_but_secrets,
    refuse_keys,
    through_the_page,
)
from zenml_mcp.resource_catalog import (
    EVENT_SOURCE_TYPES,
    FLAVOR_TEXT_FIELDS,
    get_resource_spec,
)
from zenml_mcp.resource_spec import (
    COMPONENT_TYPES,
    catalog_type,
    validate_mutation_payload,
)
from zenml_mcp.resources import (
    SDK_PAGE_SIZE,
    WriteRequest,
    exact_uuid,
    find_nested_id,
    find_nested_value,
    lost_answer,
    parses_as,
    projected,
    validated,
)

_SCHEDULE_MODES = ("cron_expression", "interval", "run_once_start_time")
_SCHEDULE_TIMES = ("run_once_start_time", "start_time", "end_time")
_EVENT_SOURCES = {
    source: catalog_type(source) for source in EVENT_SOURCE_TYPES
}
# ZenML's `TEXT_FIELD_MAX_LENGTH`.
TEXT_FIELD_MAX_LENGTH = 65535
# Upstream imports the class a flavor's or a code repository's `source` names,
# and by default allows only this package. This server imports nothing, but
# ZenML's runners import the class later, so the rule stays.
_IMPORT_PREFIX = "zenml"


def _naive_utc(value: Any) -> Any:
    """A schedule time as ZenML's trigger models send it: UTC, without an offset.

    Args:
        value: The time; anything but a string is returned unchanged.

    Returns:
        The time in ISO format, or the value as given.
    """
    if not isinstance(value, str):
        return value
    return utc_naive(value).isoformat()


def _given(payload: Mapping[str, Any], *fields: str) -> dict[str, Any]:
    return {
        field: payload[field]
        for field in fields
        if payload.get(field) is not None
    }


def _merged(existing: Any, changes: Mapping[str, Any]) -> dict[str, Any]:
    """An existing configuration with changes applied; a null removes a key.

    Args:
        existing: The stored configuration; anything but a dict counts as
            empty.
        changes: The keys to set, or to remove when null.

    Returns:
        The merged configuration.
    """
    merged = {**(existing if isinstance(existing, dict) else {}), **changes}
    return {key: value for key, value in merged.items() if value is not None}


def _component_ids(components: Mapping[str, Any]) -> dict[str, list[str]]:
    return {
        kind: [exact_uuid("component_id", item) for item in ids]
        for kind, value in components.items()
        for ids in [value if isinstance(value, list) else [value]]
    }


async def _bound_components(
    request: WriteRequest, components: Mapping[str, Any]
) -> dict[str, list[str]]:
    """Component ids by type, each checked to be a component of that type.

    The caller then reads each one the way the SDK reads it before it builds
    the stack.

    Args:
        request: The write.
        components: One id or a list of ids per component type.

    Returns:
        The ids, as a list per type.
    """
    by_type = _component_ids(components)
    for kind, ids in by_type.items():
        for component_id in ids:
            await request.checked(
                "stack_component",
                component_id,
                scoped=False,
                component_type=kind,
            )
    return by_type


async def _read_components(
    request: WriteRequest, by_type: Mapping[str, list[str]]
) -> None:
    for ids in by_type.values():
        for component_id in ids:
            await request.read("stack_component", component_id)


async def _model_version_in_project(request: WriteRequest) -> dict[str, str]:
    """The model version a service names, checked to be in the project.

    Args:
        request: The service write.

    Returns:
        The `model_version_id` field to send, or nothing when none is named.

    Raises:
        ZenMLNotFound: When the model version is not in the project.
    """
    given = request.payload.get("model_version_id")
    if not given:
        return {}
    wanted = exact_uuid("model_version_id", given)
    found = await validated(
        request.read("model_version", wanted, hydrate=False)
    )
    if (
        found.get("id") != wanted
        or find_nested_id(found, "project_id", "project") != request.project
    ):
        raise ZenMLNotFound(
            "The model version was not found in the requested project"
        )
    return {"model_version_id": wanted}


async def _create_project(request: WriteRequest) -> dict[str, Any]:
    # The SDK passes no display name, and ZenML's model then uses the name.
    return {**request.payload, "display_name": request.payload["name"]}


async def _create_stack(request: WriteRequest) -> dict[str, Any]:
    by_type = await _bound_components(request, request.payload["components"])
    await _read_components(request, by_type)
    return {
        "name": request.payload["name"],
        "description": "",
        "components": by_type,
        "service_connectors": [],
    }


async def _refuse_flavor_secrets(
    request: WriteRequest, component_type: Any, flavor: Any, configuration: Any
) -> None:
    """Refuse the fields a flavor marks as secrets, whatever their names.

    This is what `zenml_create_stack_component` does. Without the flavor
    nothing is written.

    Args:
        request: The write.
        component_type: The component's type.
        flavor: The flavor's name.
        configuration: The configuration to check.

    Raises:
        ZenMLNotFound: When no single flavor of that type has the name.
    """
    flavors = await request.client.get(
        "/flavors",
        params={
            "type": component_type,
            "name": flavor,
            "hydrate": True,
            "size": SDK_PAGE_SIZE,
        },
        what="Reading the flavor",
    )
    items = flavors.get("items") or []
    if len(items) != 1:
        raise ZenMLNotFound(
            f"No single {component_type} flavor is named {flavor!r}."
        )
    secrets = flavor_secret_keys(items[0], configuration)
    refuse_keys([f"configuration.{key}" for key in secrets])


async def _create_stack_component(request: WriteRequest) -> dict[str, Any]:
    payload = request.payload
    await _refuse_flavor_secrets(
        request,
        payload["component_type"],
        payload["flavor"],
        payload["configuration"],
    )
    return {
        "name": payload["name"],
        "type": payload["component_type"],
        "flavor": payload["flavor"],
        "configuration": payload["configuration"],
    }


async def _create_service(request: WriteRequest) -> dict[str, Any]:
    payload = request.payload
    model_version = await _model_version_in_project(request)
    given = payload["config"]
    # The defaults of the SDK's `ServiceConfig` and `ServiceType`.
    config = {
        "type": "zenml.services.service.ServiceConfig",
        "name": "",
        "description": "",
        "pipeline_name": "",
        "pipeline_step_name": "",
        "model_name": "",
        "model_version": "",
        **given,
    }
    config["service_name"] = given.get(
        "service_name", f"zenml-{config['name'] or config['model_name']}"
    )
    return {
        "name": config["service_name"],
        "service_type": {
            "name": "",
            "description": "",
            "logo_url": "",
            **payload["service_type"],
        },
        "config": config,
        "project": request.project,
        **model_version,
    }


async def _create_run_template(request: WriteRequest) -> dict[str, Any]:
    payload = request.payload
    snapshot = exact_uuid("snapshot_id", payload["snapshot_id"])
    await request.checked("snapshot", snapshot)
    return {
        "name": payload["name"],
        "source_snapshot_id": snapshot,
        "project": request.project,
        "hidden": False,
        **_given(payload, "description", "tags"),
    }


async def _create_model(request: WriteRequest) -> dict[str, Any]:
    return {
        "save_models_to_registry": True,
        **request.payload,
        "project": request.project,
    }


async def _create_model_version(request: WriteRequest) -> dict[str, Any]:
    model_id = str(request.model_id)
    await request.checked("model", model_id)
    model = await request.read("model", model_id)
    return {
        **request.payload,
        "model": model["id"],
        "project": body_of(model).get("project_id"),
    }


async def _create_tag(request: WriteRequest) -> dict[str, Any]:
    return {"exclusive": False, **request.payload}


async def _create_flavor(request: WriteRequest) -> dict[str, Any]:
    """The `FlavorRequest` the SDK builds from the flavor class, from its fields.

    Args:
        request: The flavor write.

    Returns:
        The request body.

    Raises:
        ZenMLBadRequest: When the config schema is too long for ZenML.
    """
    payload = request.payload
    if len(payload["config_schema"]) > TEXT_FIELD_MAX_LENGTH:
        # The SDK's check, on the schema's top-level keys.
        raise ZenMLBadRequest(
            "Json representation of configuration schemaexceeds max length. This "
            "could be caused by anoverly long docstring on the flavors "
            "configuration class' docstring."
        )
    return {
        "name": payload["name"],
        "type": payload["component_type"],
        "source": payload["source"],
        "config_schema": payload["config_schema"],
        "integration": "custom",
        "is_custom": True,
        **_given(payload, *FLAVOR_TEXT_FIELDS),
    }


async def _create_code_repository(request: WriteRequest) -> dict[str, Any]:
    payload = request.payload
    path = payload["source"].split("@", 1)[0]
    module, _, attribute = path.rpartition(".")
    return {
        "name": payload["name"],
        "config": payload["config"],
        # The SDK's `Source.from_import_path`: the module is everything before
        # the last dot.
        "source": {
            "module": module or path,
            "attribute": attribute if module else None,
            "type": "unknown",
        },
        "project": request.project,
        **_given(payload, "description", "logo_url"),
    }


def _new_trigger(request: WriteRequest, **fields: Any) -> dict[str, Any]:
    trigger_kind = request.spec.rest.list_defaults
    return {
        "project": request.project,
        "name": request.payload["name"],
        "type": trigger_kind["type"],
        "flavor": trigger_kind["flavor"],
        "active": request.payload.get("active", True),
        "concurrency": request.payload.get("concurrency", "skip"),
        **fields,
    }


async def _create_schedule_trigger(request: WriteRequest) -> dict[str, Any]:
    payload = request.payload
    schedule = _given(
        payload, *_SCHEDULE_MODES, "start_time", "end_time", "max_runs"
    )
    for field in _SCHEDULE_TIMES:
        if field in schedule:
            schedule[field] = _naive_utc(schedule[field])
    return _new_trigger(request, **schedule)


async def _create_platform_event_trigger(
    request: WriteRequest,
) -> dict[str, Any]:
    payload = request.payload
    source = exact_uuid("source_id", payload["source_id"])
    await request.checked(_EVENT_SOURCES[payload["source_type"]], source)
    return _new_trigger(
        request,
        source_entity={"id": source, "type": payload["source_type"]},
        target_events=payload["target_events"],
    )


async def _create_webhook_trigger(request: WriteRequest) -> dict[str, Any]:
    payload = request.payload
    webhook_id = exact_uuid("webhook_id", payload["webhook_id"])
    await request.checked("webhook", webhook_id)
    webhook = await request.read("webhook", webhook_id)
    # The SDK sends the configuration as the webhook's provider class
    # normalizes it. ZenML normalizes it again on receipt.
    return _new_trigger(
        request,
        webhook_id=webhook["id"],
        configuration=payload["configuration"],
    )


async def _create_webhook(request: WriteRequest) -> dict[str, Any]:
    payload = request.payload
    return {
        "project": request.project,
        "name": payload["name"],
        "webhook_type": payload["webhook_type"],
        "active": payload.get("active", True),
        **_given(payload, "secret"),
    }


Body = Callable[[WriteRequest], Awaitable[dict[str, Any]]]
_CREATE: Mapping[str, Body] = {
    "project": _create_project,
    "stack": _create_stack,
    "stack_component": _create_stack_component,
    "service_connector": create_service_connector,
    "service": _create_service,
    "run_template": _create_run_template,
    "model": _create_model,
    "model_version": _create_model_version,
    "tag": _create_tag,
    "flavor": _create_flavor,
    "code_repository": _create_code_repository,
    "webhook": _create_webhook,
    "schedule_trigger": _create_schedule_trigger,
    "platform_event_trigger": _create_platform_event_trigger,
    "webhook_trigger": _create_webhook_trigger,
}


def _or_existing(payload: Mapping[str, Any], entity: Any, field: str) -> Any:
    given = payload.get(field)
    return field_of(entity, field) if given is None else given


async def _update_project(
    request: WriteRequest, project: Any
) -> dict[str, Any]:
    payload = request.payload
    return {
        "name": payload.get("name") or project.get("name"),
        "display_name": payload.get("display_name")
        or field_of(project, "display_name"),
        **_given(payload, "description"),
    }


async def _check_stack_update(request: WriteRequest) -> None:
    updates = request.payload.get("component_updates")
    if updates:
        await _bound_components(request, updates)


async def _update_stack(request: WriteRequest, stack: Any) -> dict[str, Any]:
    payload = request.payload
    body: dict[str, Any] = {"stack_spec_path": None}
    if payload.get("name"):
        if await request.taken(payload["name"]):
            raise ZenMLAlreadyExists(
                f"A stack named {payload['name']!r} already exists. "
                "Choose another name."
            )
        body["name"] = payload["name"]
    body |= _given(payload, "description")
    if payload.get("component_updates"):
        updates = _component_ids(payload["component_updates"])
        await _read_components(request, updates)
        current = meta_of(stack).get("components") or {}
        body["components"] = {
            **{
                kind: [item["id"] for item in items]
                for kind, items in current.items()
            },
            **updates,
        }
    return body


async def _check_component_update(request: WriteRequest) -> None:
    connector = request.payload.get("connector_id")
    if connector:
        await request.checked(
            "service_connector",
            exact_uuid("connector_id", connector),
            scoped=False,
        )


async def _update_stack_component(
    request: WriteRequest, component: Any
) -> dict[str, Any]:
    payload = request.payload
    body: dict[str, Any] = {}
    if payload.get("name") is not None:
        if await request.taken(payload["name"], type=request.component_type):
            raise ZenMLAlreadyExists(
                f"A {request.component_type} named {payload['name']!r} already "
                "exists. Choose another name."
            )
        body["name"] = payload["name"]
    metadata = meta_of(component)
    if payload.get("configuration") is not None:
        await _refuse_flavor_secrets(
            request,
            request.component_type,
            body_of(component).get("flavor_name"),
            payload["configuration"],
        )
        body["configuration"] = _merged(
            metadata.get("configuration"), payload["configuration"]
        )
    connector = payload.get("connector_id")
    resource_id = payload.get("connector_resource_id")
    if payload.get("disconnect"):
        connector = resource_id = None
    else:
        # The SDK reads the component again here, and keeps the connector it
        # has when the caller names none.
        current = meta_of(
            await request.read("stack_component", str(request.target))
        )
        if connector is not None:
            connector = exact_uuid("connector_id", connector)
        elif current.get("connector"):
            connector = current["connector"].get("id")
            resource_id = current.get("connector_resource_id")
    return {
        **body,
        "connector": connector,
        "connector_resource_id": resource_id,
    }


async def _update_service(request: WriteRequest, _: Any) -> dict[str, Any]:
    # The SDK sets only the fields that are not empty.
    body = {field: value for field, value in request.payload.items() if value}
    if "model_version_id" in body:
        body["model_version_id"] = exact_uuid(
            "model_version_id", body["model_version_id"]
        )
    return body


async def _update_tag(request: WriteRequest, _: Any) -> dict[str, Any]:
    return dict(request.payload)


async def _update_always_sent(request: WriteRequest, _: Any) -> dict[str, Any]:
    fields = request.spec.always_sent
    body = {field: request.payload.get(field) for field in fields}
    if "force" in body:
        body["force"] = bool(body["force"])
    return body


async def _update_code_repository(
    request: WriteRequest, repository: Any
) -> dict[str, Any]:
    body = await _update_always_sent(request, repository)
    if request.payload.get("config") is not None:
        body["config"] = _merged(
            meta_of(repository).get("config"), request.payload["config"]
        )
    return body


def _named_state(payload: Mapping[str, Any]) -> dict[str, Any]:
    """A trigger's `active` and `concurrency`, as far as an update names them.

    ZenML keeps what a schedule or platform event trigger update leaves out
    of these, so an update that doesn't name them can't undo a change made
    since the read.

    Args:
        payload: The update's payload.

    Returns:
        The ones the update names.
    """
    return {
        field: payload[field]
        for field in ("active", "concurrency")
        if payload.get(field) is not None
    }


async def _update_schedule_trigger(
    request: WriteRequest, trigger: Any
) -> dict[str, Any]:
    payload = request.payload
    trigger_kind = request.spec.rest.list_defaults
    # Naming one way to schedule replaces the other two.
    reschedules = any(
        payload.get(mode) is not None for mode in _SCHEDULE_MODES
    )
    body = {
        "name": payload.get("name") or field_of(trigger, "name"),
        "type": trigger_kind["type"],
        "flavor": trigger_kind["flavor"],
        "max_runs": payload.get("max_runs") or field_of(trigger, "max_runs"),
        "next_occurrence": None,
        **{
            mode: payload.get(mode) if reschedules else field_of(trigger, mode)
            for mode in _SCHEDULE_MODES
        },
        **{
            field: _or_existing(payload, trigger, field)
            for field in ("start_time", "end_time")
        },
        **_named_state(payload),
    }
    return {
        **body,
        **{field: _naive_utc(body[field]) for field in _SCHEDULE_TIMES},
    }


def _event_source(payload: Mapping[str, Any], item: Any) -> tuple[str, str]:
    """The source a platform event trigger has after an update.

    What the payload names, else the trigger's `source_entity`. Upstream
    looked for flat `source_type` and `source_id` keys, which ZenML doesn't
    return, and so refused any update that didn't name both.

    Args:
        payload: The update's payload.
        item: The trigger as ZenML returns it.

    Returns:
        The source's type and id.

    Raises:
        ZenMLBadRequest: When the source is not known, or its type is not a
            platform event source.
    """
    stored = field_of(item, "source_entity") or {}
    source_type = payload.get("source_type") or stored.get("type")
    source_id = payload.get("source_id") or stored.get("id")
    if source_type is None or source_id is None:
        raise ZenMLBadRequest(
            "Unable to validate the effective platform-event source"
        )
    if source_type not in _EVENT_SOURCES:
        raise ZenMLBadRequest("Invalid platform-event source_type")
    return str(source_type), exact_uuid("source_id", str(source_id))


async def _update_platform_event_trigger(
    request: WriteRequest, trigger: Any
) -> dict[str, Any]:
    payload = request.payload
    trigger_kind = request.spec.rest.list_defaults
    return {
        "name": payload.get("name") or field_of(trigger, "name"),
        "type": trigger_kind["type"],
        "flavor": trigger_kind["flavor"],
        **_named_state(payload),
        # Checked before the write, in `_send`.
        "source_entity": {
            "type": payload["source_type"],
            "id": payload["source_id"],
        },
        "target_events": payload.get("target_events")
        or field_of(trigger, "target_events"),
    }


async def _update_webhook_trigger(
    request: WriteRequest, trigger: Any
) -> dict[str, Any]:
    payload = request.payload
    if payload.get("configuration") is not None:
        # The SDK reads the webhook to normalize the configuration with its
        # provider class. ZenML normalizes it on receipt.
        await request.read("webhook", str(field_of(trigger, "webhook_id")))
    return {
        "type": request.spec.rest.list_defaults["type"],
        **{
            field: _or_existing(payload, trigger, field)
            for field in ("name", "active", "concurrency", "configuration")
        },
    }


Update = Callable[[WriteRequest, Any], Awaitable[dict[str, Any]]]
# The other types send their `always_sent` fields.
_UPDATE: Mapping[str, Update] = {
    "project": _update_project,
    "stack": _update_stack,
    "stack_component": _update_stack_component,
    "service_connector": update_service_connector,
    "service": _update_service,
    "tag": _update_tag,
    "code_repository": _update_code_repository,
    "schedule_trigger": _update_schedule_trigger,
    "platform_event_trigger": _update_platform_event_trigger,
    "webhook_trigger": _update_webhook_trigger,
}
# What upstream checks about related entities before an update.
_UPDATE_CHECKS: Mapping[str, Callable[[WriteRequest], Awaitable[Any]]] = {
    "stack": _check_stack_update,
    "stack_component": _check_component_update,
    "service": _model_version_in_project,
}


async def _delete_params(request: WriteRequest) -> dict[str, Any] | None:
    """The query a delete is sent with.

    Like the SDK, an artifact version that runs still use keeps its metadata.

    Args:
        request: The delete.

    Returns:
        The query parameters, or None when the delete sends none.

    Raises:
        ZenMLBadRequest: When the delete would remove the metadata of an
            artifact version that runs use.
    """
    resource_type, target = request.spec.resource_type, request.target
    if request.spec.trigger:
        return {"soft": True}
    if resource_type != "artifact_version":
        return None
    metadata = request.payload.get("delete_metadata", True)
    data = request.payload.get("delete_from_artifact_store", False)
    if metadata:
        unused = await request.client.get(
            "/artifact_versions",
            params={
                "id": target,
                "only_unused": True,
                "size": 1,
                "project": request.project,
                "hydrate": False,
            },
            what="Checking that no run uses the artifact version",
        )
        if not unused.get("items"):
            raise ZenMLBadRequest(
                "The metadata of an artifact version that runs use cannot be "
                "deleted. Delete the runs that use it first."
            )
    if not data:
        return None
    return {"delete_metadata": metadata, "delete_from_artifact_store": True}


def _reconciliation_by_id(
    request: WriteRequest, operation: str, resource_id: str
) -> dict[str, Any]:
    """The read of a written resource whose id is known, as upstream names it.

    Args:
        request: The write.
        operation: `create`, `update` or `delete`.
        resource_id: The written resource's id.

    Returns:
        The read that confirms the write's outcome.
    """
    resource_type, payload = request.spec.resource_type, request.payload
    project = {"project_id": request.project} if request.project else {}
    if request.spec.trigger and operation == "delete":
        return {
            "operation": "list",
            "resource_type": resource_type,
            "filters": {"id": resource_id, "is_archived": True},
            **project,
            "note": "Confirm that the trigger is archived.",
        }
    component_type = request.component_type or (
        payload.get("component_type")
        if resource_type == "stack_component"
        else None
    )
    result = {
        "operation": "get",
        "resource_type": resource_type,
        "resource_id": resource_id,
        **project,
        **(
            {"artifact_id": request.artifact_id} if request.artifact_id else {}
        ),
        **({"model_id": request.model_id} if request.model_id else {}),
        **({"component_type": component_type} if component_type else {}),
    }
    if resource_type == "artifact_version" and operation == "delete":
        result["note"] = (
            "A remaining metadata record cannot prove whether stored data was deleted."
        )
    return result


def _reconciliation_by_name(request: WriteRequest) -> dict[str, Any]:
    """The read of a created resource, by name, used when no resource id is available.

    Args:
        request: The create.

    Returns:
        The read that confirms the create's outcome, or a note that none can
        when the request doesn't identify the new resource.
    """
    resource_type, payload = request.spec.resource_type, request.payload
    project = {"project_id": request.project} if request.project else {}
    if resource_type == "model_version" and "name" not in payload:
        return {
            "operation": None,
            "resource_type": resource_type,
            **project,
            "model_id": request.model_id,
            "new_version_id": None,
            "reconcilable": False,
            "note": (
                "The model version may have been created with an auto-generated name, "
                "but its ID was lost with the response. The model ID alone cannot "
                "identify the new version; do not retry automatically."
            ),
        }
    if resource_type == "flavor":
        return {
            "operation": None,
            "resource_type": resource_type,
            "source": payload["source"],
            "component_type": payload["component_type"],
            "new_flavor_id": None,
            "reconcilable": False,
            "note": (
                "The flavor may have been created, but its generated ID and name were "
                "lost with the response. Source and component type do not uniquely "
                "identify it; do not retry automatically."
            ),
        }
    if resource_type == "service":
        config = payload["config"]
        default = f"zenml-{config.get('name') or config.get('model_name')}"
        filters = {"service_name": config.get("service_name", default)}
    elif resource_type == "stack_component":
        filters = {"name": payload["name"], "type": payload["component_type"]}
    else:
        filters = {"name": payload["name"]} if "name" in payload else {}
    if resource_type == "model_version" and request.model_id:
        filters["model_id"] = request.model_id
    return {
        "operation": "list",
        "resource_type": resource_type,
        "filters": filters,
        **project,
        "note": (
            "An auto-generated webhook secret cannot be recovered after an unknown "
            "create outcome."
            if resource_type == "webhook" and "secret" not in payload
            else "Confirm the mutation by reading the resource; do not repeat it "
            "automatically."
        ),
    }


def _named_by_a_schema(
    resource_type: str, operation: str, payload: Any
) -> Any:
    """The payload without a flavor's `config_schema`.

    The schema names fields and holds none of their values, so its key names
    are not checked for credentials.

    Args:
        resource_type: The catalogued type written.
        operation: The operation.
        payload: The write's payload.

    Returns:
        The payload, without `config_schema` for a flavor create.
    """
    if (resource_type, operation) == ("flavor", "create") and isinstance(
        payload, dict
    ):
        return {
            key: value
            for key, value in payload.items()
            if key != "config_schema"
        }
    return payload


async def _checked_request(
    call: ZenMLCall,
    resource_type: str,
    operation: str,
    *,
    resource_id: str | None,
    payload: dict[str, Any] | None,
    project_id: str | None,
    parents: Mapping[str, str | None],
    through: frozenset[tuple[str, str]],
) -> tuple[WriteRequest, dict[str, Any]]:
    """A request that passed every check upstream makes before its reads.

    The caller's session is opened for the first read: the default project,
    for a type the SDK creates only there, or else after every check.

    Args:
        call: The tool call.
        resource_type: The catalogued type written.
        operation: `create`, `update` or `delete`.
        resource_id: The resource, for an update or a delete.
        payload: The operation's payload.
        project_id: The project, for a project-scoped type.
        parents: Parent ids, such as `model_id`.
        through: The secret writes that go through the secret page.

    Returns:
        The checked request, and the scope its answer reports.

    Raises:
        ZenMLBadRequest: When the project, the parent ids, the component
            type or a flavor's or code repository's source is not valid
            for the write, or the project is not the caller's default
            project for a type the SDK creates only there.
    """
    refuse_credentials_but_secrets(
        resource_type,
        operation,
        _named_by_a_schema(resource_type, operation, payload),
        through,
    )
    spec = get_resource_spec(resource_type)
    mutation = spec.mutation(operation)
    checked = validate_mutation_payload(spec, operation, payload)
    ask_if_sensitive(call, mutation.sensitive, checked)
    scope: dict[str, Any] = {"kind": "global"}
    project = None
    if spec.scope == "global":
        if project_id is not None:
            raise ZenMLBadRequest(
                f"{resource_type!r} is global and does not accept project_id"
            )
    elif project_id is None:
        raise ZenMLBadRequest(
            f"project_id is required for {resource_type!r} {operation}"
        )
    else:
        project = exact_uuid("project_id", project_id)
        scope = {
            "kind": "project",
            "project_id": project,
            "source": "requested",
        }
    client = None
    if (
        operation == "create"
        and spec.created_in_active_project
        and (resource_type, operation) not in through
    ):
        # A write withheld for the secret page reads nothing before its link;
        # the page checks the project when it runs the write.
        client = call.client
        if project != await validated(default_project_id(client)):
            raise ZenMLBadRequest(
                "The requested project is not the client's active project"
            )
    target = (
        None
        if operation == "create"
        else exact_uuid("resource_id", resource_id)
    )
    missing = sorted(f for f in mutation.parent_fields if not parents.get(f))
    unexpected = sorted(
        field
        for field, value in parents.items()
        if value is not None and field not in mutation.parent_fields
    )
    if missing:
        raise ZenMLBadRequest(
            f"{resource_type!r} {operation} requires: {', '.join(missing)}"
        )
    if unexpected:
        raise ZenMLBadRequest(
            f"Unexpected identifiers for {resource_type!r} {operation}: "
            f"{', '.join(unexpected)}"
        )
    ids = {
        parent: exact_uuid(parent, parents[parent])
        for parent in ("artifact_id", "model_id")
        if parents.get(parent) is not None
    }
    component_type = parents.get("component_type")
    if "component_type" in mutation.parent_fields and (
        component_type not in COMPONENT_TYPES
    ):
        raise ZenMLBadRequest("Invalid component_type")
    module = str(checked.get("source") or _IMPORT_PREFIX).split(":", 1)[0]
    if module != _IMPORT_PREFIX and not module.startswith(
        f"{_IMPORT_PREFIX}."
    ):
        raise ZenMLBadRequest(
            f"source must be a {resource_type.replace('_', ' ')} class that ships "
            f"with ZenML (a path under `{_IMPORT_PREFIX}.`)."
        )
    request = WriteRequest(
        client=call.client if client is None else client,
        spec=spec,
        payload=checked,
        project=project,
        target=target,
        artifact_id=ids.get("artifact_id"),
        model_id=ids.get("model_id"),
        component_type=component_type,
    )
    return request, scope


async def _send(request: WriteRequest, operation: str) -> Any:
    """Read what upstream and the SDK read, then send the one write.

    Args:
        request: The checked request.
        operation: `create`, `update` or `delete`.

    Returns:
        ZenML's answer, or None when the write waits for the secret page.

    Raises:
        ZenMLBadRequest: When the write would delete the caller's default
            project.
    """
    client, spec = request.client, request.spec
    resource_type, route = spec.resource_type, request.route
    label = resource_type.replace("_", " ")
    if operation == "create":
        body = await _CREATE[resource_type](request)
        if request.asking:
            return None
        return await client.write(
            "POST", route, json=body, what=f"Creating the {label}"
        )
    target = str(request.target)
    existing = await request.checked(
        resource_type,
        target,
        artifact_id=request.artifact_id,
        model_id=request.model_id,
        component_type=request.component_type,
    )
    if operation == "update" and resource_type in _UPDATE_CHECKS:
        await _UPDATE_CHECKS[resource_type](request)
    if operation == "update" and resource_type == "platform_event_trigger":
        source_type, source_id = _event_source(
            request.payload, existing["item"]
        )
        await request.checked(_EVENT_SOURCES[source_type], source_id)
        # The update sends the source checked here, not one read again later.
        request = replace(
            request,
            payload={
                **request.payload,
                "source_type": source_type,
                "source_id": source_id,
            },
        )
    if (resource_type, operation) == ("project", "delete") and (
        target == await request.default_project()
    ):
        # The SDK refuses to delete its active project, and so does upstream.
        raise ZenMLBadRequest("Your default project cannot be deleted.")
    entity = None
    if operation not in spec.not_read_first:
        entity = await request.read(
            resource_type, target, hydrate=not spec.read_unhydrated
        )
    path = f"{route}/{segment(target)}"
    if operation == "delete":
        return await client.write(
            "DELETE",
            path,
            params=await _delete_params(request),
            what=f"Deleting the {label}",
        )
    body = await _UPDATE.get(resource_type, _update_always_sent)(
        request, entity
    )
    if request.asking:
        return None
    return await client.write(
        "PUT", path, json=body, what=f"Updating the {label}"
    )


def _without(
    error: ZenMLRestError, values: list[str] | None
) -> ZenMLRestError:
    """The error without the stored secrets the write resent.

    ZenML's answer can echo one, and a caller never sees a stored secret.
    The answer was cut to a length before it got here, so a cut secret's
    start is masked too.

    Args:
        error: ZenML's error.
        values: The secrets the write resent, if any.

    Returns:
        A copy of the error with each secret masked, or the error itself
        when there is none.
    """
    if not values:
        return error
    scrubbed = copy.copy(error)
    for value in values:
        scrubbed.message = scrubbed.message.replace(value, "***")
        # The longest start of the secret the cut left, of 4 characters or
        # more: shorter ones are too common to tell from other text.
        for length in range(len(value) - 1, 3, -1):
            if value[:length] in scrubbed.message:
                scrubbed.message = scrubbed.message.replace(
                    value[:length], "***"
                )
                break
    scrubbed.args = (scrubbed.message,)
    return scrubbed


def _unknown_mutation(
    request: WriteRequest,
    operation: str,
    scope: dict[str, Any],
    reconciliation: dict[str, Any],
) -> Any:
    """mcp-zenml's answer to a write whose response was lost.

    That answer is a `CallToolResult`, which the SDK passes through.

    Args:
        request: The write.
        operation: `create`, `update` or `delete`.
        scope: The scope the answer reports.
        reconciliation: The read that confirms the write's outcome.

    Returns:
        The tool result that reports the outcome as unknown.
    """
    unknown = request.outcome(
        scope, reconciliation, operation=operation, outcome="unknown"
    )
    recovery = (
        "Use the supplied reconciliation read and do not repeat automatically."
        if reconciliation.get("operation")
        else "The created resource cannot be identified from the request; "
        "do not retry automatically."
    )
    return lost_answer(
        f"zenml_{operation}_resource", "mutation", recovery, unknown
    )


async def mutate(
    call: ZenMLCall,
    resource_type: str,
    operation: str,
    *,
    resource_id: str | None = None,
    payload: dict[str, Any] | None,
    project_id: str | None,
    **parents: str | None,
) -> dict[str, Any]:
    """Create, update or delete one resource, as the generic write tools do.

    Args:
        call: The tool call.
        resource_type: The catalogued type.
        operation: `create`, `update` or `delete`.
        resource_id: The resource, for an update or a delete.
        payload: The operation's payload.
        project_id: The project, for a project-scoped type.
        **parents: Parent ids, such as `model_id`.

    Returns:
        The write's outcome, or a secret page's answer.

    Raises:
        ZenMLBadRequest: When ZenML's answer can't be read.
        ZenMLRestError: When ZenML refused or failed the write.
    """  # noqa: DOC503
    through = through_the_page(call)
    request, scope = await _checked_request(
        call,
        resource_type,
        operation,
        resource_id=resource_id,
        payload=payload,
        project_id=project_id,
        parents=parents,
        through=through,
    )
    arguments = {
        "resource_type": resource_type,
        "payload": request.payload,
        "project_id": project_id,
        **({"resource_id": resource_id} if resource_id else {}),
        **{
            name: value for name, value in parents.items() if value is not None
        },
    }
    tool = f"zenml_{operation}_resource"
    if (resource_type, operation) in through and resource_type == "webhook":
        return awaiting_user(call, tool, arguments, (WEBHOOK_SECRET,))
    # Stored secrets a write sends again stay out of its errors, page or not.
    request = replace(request, resent=[])
    if (resource_type, operation) in through:
        # The write is built as the page builds it, reads included; a
        # connector whose call needs no secret is then written directly.
        request = replace(request, asking=[])
    reconciliation = (
        _reconciliation_by_name(request)
        if operation == "create"
        else _reconciliation_by_id(request, operation, str(request.target))
    )
    try:
        result = await _send(request, operation)
    except (ZenMLOutcomeUnknown, ZenMLUnavailable) as error:
        if not answer_lost(error):
            raise _without(error, request.resent) from None
        return _unknown_mutation(request, operation, scope, reconciliation)
    except ZenMLRestError as error:
        raise _without(error, request.resent) from None
    if request.asking:
        return awaiting_user(call, tool, arguments, request.asking)
    answered = result.get("id") if isinstance(result, dict) else None
    if isinstance(result, str) or (
        operation != "delete" and not parses_as(resource_type, result)
    ):
        # As the SDK fails to parse it: upstream reports invalid input, though
        # the write may have been applied.
        raise ZenMLBadRequest(UNREADABLE)
    if resource_type == "service_connector" and operation != "delete":
        result = connector_as_the_sdk_holds(result)
    if operation == "create" and request.spec.get_fields is not None:
        reconciliation = _reconciliation_by_id(
            request, operation, str(answered)
        )
    response = request.outcome(
        scope,
        reconciliation,
        operation=operation,
        outcome="completed",
        resource_id=answered or request.target,
    )
    if result is not None:
        response["item"] = projected(result, resource_type=resource_type)
    if (resource_type, operation) == ("webhook", "create"):
        issued = find_nested_value(result, "secret")
        if issued is not None:
            response["issued_secret"] = issued
    if request.spec.trigger and operation == "delete":
        response["archived"] = True
    if resource_type == "artifact_version" and operation == "delete":
        response["delete_metadata"] = request.payload.get(
            "delete_metadata", True
        )
        # ZenML answers a delete with no body, so nothing confirms the data went:
        # report what was asked for, never that it happened.
        asked = request.payload.get("delete_from_artifact_store", False)
        response["data_deletion"] = (
            "not confirmed" if asked else "not requested"
        )
    return response
