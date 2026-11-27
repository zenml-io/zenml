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
"""The resource types the generic tools offer, one record each.

The contract of each type (filters, schemas, operations and actions) is
mcp-zenml's `zenml_resource_registry.py` data (commit 3de0643), without what
`not_offered` leaves out and with flavor create taking the fields of the built
flavor, because this server imports no Python class. The rest of each record is how the
ZenML SDK reaches the type over REST, and what its writes send (ZenML 0.97.0,
`client.py` and `rest_zen_store.py`).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from itertools import combinations
from types import MappingProxyType
from typing import Any

from zenml_mcp.call import Sensitive
from zenml_mcp.client import ZenMLBadRequest
from zenml_mcp.resource_spec import (
    _ENUM_FILTERS,
    COMPONENT_TYPE_SCHEMA,
    CONCURRENCY,
    MODEL_STAGES,
    TAGGABLE_RESOURCE,
    UUID_SCHEMA,
    ActionSpec,
    Mutation,
    MutationSpec,
    ResourceSpec,
    Rest,
    ScopeKind,
)

_STR = {"type": "string"}
_NONEMPTY = {"type": "string", "minLength": 1}
_BOOL = {"type": "boolean"}
_POSITIVE_INT = {"type": "integer", "minimum": 1}
_STRING_LIST = {"type": "array", "items": _NONEMPTY}
_STRING_MAP = {"type": "object", "additionalProperties": {"type": "string"}}
_NONNEGATIVE_INT = {"type": "integer", "minimum": 0}
_NULLABLE_STRING_MAP = {
    "type": "object",
    "additionalProperties": {"anyOf": [{"type": "string"}, {"type": "null"}]},
}
_CONFIG_MAP = {"type": "object", "additionalProperties": True}
_ANY_MAP = {"type": "object"}


def _stack_components_schema(*, require_core: bool) -> dict[str, Any]:
    binding = {
        "anyOf": [
            UUID_SCHEMA,
            {"type": "array", "items": UUID_SCHEMA, "minItems": 1},
        ]
    }
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            component_type: binding
            for component_type in COMPONENT_TYPE_SCHEMA["enum"]
        },
        "additionalProperties": False,
    }
    if require_core:
        schema["required"] = ["orchestrator", "artifact_store"]
    return schema


_COLOR = {"type": "string", "enum": list(_ENUM_FILTERS[("tag", "color")])}
_CONCURRENCY = {"type": "string", "enum": list(CONCURRENCY)}
_MODEL_STAGE = {"type": "string", "enum": list(MODEL_STAGES)}
# What a platform event trigger's source can be, as ZenML names it.
EVENT_SOURCE_TYPES = ("pipeline", "pipeline_run", "pipeline_snapshot")
_SOURCE_TYPE = {"type": "string", "enum": list(EVENT_SOURCE_TYPES)}
_DATETIME = {"type": "string", "format": "date-time"}

# The optional text fields of ZenML's `FlavorRequest`.
FLAVOR_TEXT_FIELDS = (
    "display_name",
    "connector_type",
    "connector_resource_type",
    "connector_resource_id_attr",
    "logo_url",
    "docs_url",
    "sdk_docs_url",
)


def _mutation(
    operation: Mutation,
    properties: Mapping[str, dict[str, Any]] | None = None,
    *,
    required: tuple[str, ...] = (),
    parents: tuple[str, ...] = (),
    payload_required: bool | None = None,
    constraints: Mapping[str, Any] | None = None,
    example: Mapping[str, Any] | None = None,
    sensitive: Sensitive | None = None,
) -> MutationSpec:
    return MutationSpec(
        operation=operation,
        payload_properties=MappingProxyType(dict(properties or {})),
        required_payload=required,
        parent_fields=parents,
        payload_required=bool(properties)
        if payload_required is None
        else payload_required,
        payload_constraints=MappingProxyType(dict(constraints or {})),
        example_payload=MappingProxyType(dict(example))
        if example is not None
        else None,
        sensitive=sensitive,
    )


_DELETE = _mutation("delete", payload_required=False)


def _required(*fields: str) -> dict[str, Any]:
    return {"type": "object", "required": list(fields)}


def _only(fields: tuple[str, ...], *excluded: str) -> dict[str, Any]:
    """Require `fields` and none of `excluded`.

    Args:
        fields: The fields an object must have.
        excluded: The fields it must not have.

    Returns:
        The JSON schema.
    """
    return {
        **_required(*fields),
        "not": {"anyOf": [_required(field) for field in excluded]},
    }


_CARD_FIELDS: dict[str, dict[str, Any]] = {
    "name": _NONEMPTY,
    "license": _STR,
    "description": _STR,
    "audience": _STR,
    "use_cases": _STR,
    "limitations": _STR,
    "trade_offs": _STR,
    "ethics": _STR,
}
_TAG_UPDATES = {"add_tags": _STRING_LIST, "remove_tags": _STRING_LIST}
_TRIGGER_COMMON: dict[str, dict[str, Any]] = {
    "name": _NONEMPTY,
    "active": _BOOL,
    "concurrency": _CONCURRENCY,
}
_SCHEDULE_TRIGGER_FIELDS: dict[str, dict[str, Any]] = {
    **_TRIGGER_COMMON,
    "cron_expression": _NONEMPTY,
    "interval": {"type": "integer", "minimum": 60},
    "run_once_start_time": _DATETIME,
    "start_time": _DATETIME,
    "end_time": _DATETIME,
    "max_runs": _POSITIVE_INT,
}
_EVENT_TRIGGER_FIELDS: dict[str, dict[str, Any]] = {
    **_TRIGGER_COMMON,
    "source_type": _SOURCE_TYPE,
    "source_id": UUID_SCHEMA,
    "target_events": {"type": "array", "items": _NONEMPTY, "minItems": 1},
}

_REPLAY_CONFIGURATION = {
    "type": "object",
    "properties": {
        "skip_successful_steps": _BOOL,
        "steps_to_skip": {
            "type": "array",
            "items": _NONEMPTY,
            "uniqueItems": True,
        },
        "step_input_overrides": {
            "type": "object",
            "additionalProperties": _CONFIG_MAP,
        },
        "step_default_input_overrides": {
            "type": "object",
            "additionalProperties": _CONFIG_MAP,
        },
    },
    "additionalProperties": False,
}
_TRIGGER_RUN_CONFIGURATION = {
    "type": "object",
    "properties": {
        "run_name": _NONEMPTY,
        "enable_cache": _BOOL,
        "enable_artifact_metadata": _BOOL,
        "enable_artifact_visualization": _BOOL,
        "enable_step_logs": _BOOL,
        "enable_pipeline_logs": _BOOL,
        "enable_heartbeat": _BOOL,
        "substitutions": _STRING_MAP,
        "execution_mode": {
            "type": "string",
            "enum": ["fail_fast", "stop_on_failure", "continue_on_failure"],
        },
    },
    "additionalProperties": False,
}


def _action(
    resource_type: str,
    action: str,
    sdk_method: str,
    properties: Mapping[str, dict[str, Any]] | None = None,
    *,
    required: tuple[str, ...] = (),
    returns: bool = False,
    sensitive: Sensitive | None = None,
) -> ActionSpec:
    return ActionSpec(
        resource_type=resource_type,
        action=action,
        sdk_method=sdk_method,
        payload_properties=MappingProxyType(dict(properties or {})),
        required_payload=required,
        returns=returns,
        sensitive=sensitive,
    )


_COMMON = ("sort_by", "logical_operator", "id", "created", "updated")


def _filters(*fields: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys((*_COMMON, *fields)))


def _resource(
    resource_type: str,
    description: str,
    *,
    rest: Rest,
    scope: ScopeKind = "project",
    default_size: int = 20,
    filters: tuple[str, ...],
    list_required_filters: tuple[str, ...] = (),
    get_fields: tuple[str, ...] | None = ("resource_id",),
    non_paginated: bool = False,
    mutations: tuple[MutationSpec, ...] = (),
    actions: tuple[ActionSpec, ...] = (),
    not_offered: Mapping[str, str] | None = None,
    secret_fields: Mapping[str, str] | None = None,
    noop_when_empty: tuple[str, ...] = (),
    noop_when_false: tuple[str, ...] = (),
    parent: tuple[str, str] | None = None,
    named_response: bool = True,
    omitted_fields: tuple[str, ...] = (),
    created_in_active_project: bool = False,
    not_read_first: tuple[Mutation, ...] = (),
    read_unhydrated: bool = False,
    always_sent: tuple[str, ...] = (),
) -> ResourceSpec:
    return ResourceSpec(
        resource_type=resource_type,
        description=description,
        rest=rest,
        scope=scope,
        default_size=default_size,
        list_filters=filters,
        list_required_filters=list_required_filters,
        get_fields=get_fields,
        get_required=get_fields or ("resource_id",),
        non_paginated=non_paginated,
        mutations=MappingProxyType({m.operation: m for m in mutations}),
        actions=MappingProxyType({a.action: a for a in actions}),
        not_offered=MappingProxyType(dict(not_offered or {})),
        secret_fields=MappingProxyType(dict(secret_fields or {})),
        noop_when_empty=frozenset(noop_when_empty),
        noop_when_false=frozenset(noop_when_false),
        parent=parent,
        named_response=named_response,
        omitted_fields=frozenset(omitted_fields),
        created_in_active_project=created_in_active_project,
        not_read_first=frozenset(not_read_first),
        read_unhydrated=read_unhydrated,
        always_sent=always_sent,
    )


def _trigger(
    resource_type: str,
    description: str,
    *,
    flavor: str,
    kind: str,
    filters: tuple[str, ...],
    mutations: tuple[MutationSpec, ...],
) -> ResourceSpec:
    """A trigger type.

    The trigger types share one route, where the SDK tells them apart by
    `type` and `flavor`, and the same three actions. A trigger attached to a
    snapshot starts runs when it is switched on, rescheduled or
    reconfigured, so each of its writes is sensitive, as is attaching it.

    Args:
        resource_type: The type's catalog name.
        description: What the catalog says the type is.
        flavor: The trigger flavor the SDK lists it by.
        kind: The trigger `type` the SDK lists it by.
        filters: The list filters it takes.
        mutations: The writes it offers.

    Returns:
        The type's record.
    """
    label = resource_type.replace("_", " ")
    return _resource(
        resource_type,
        description,
        rest=Rest(
            "/triggers",
            list_defaults={
                "is_archived": False,
                "flavor": flavor,
                "type": kind,
            },
        ),
        actions=(
            _action(
                resource_type,
                "attach",
                "attach_trigger_to_snapshot",
                {
                    "snapshot_id": UUID_SCHEMA,
                    "allow_replace": _BOOL,
                    "run_configuration": _TRIGGER_RUN_CONFIGURATION,
                },
                required=("snapshot_id",),
                sensitive=Sensitive(f"Attaching a {label} to a snapshot"),
            ),
            _action(
                resource_type,
                "detach",
                "detach_trigger_from_snapshot",
                {"snapshot_id": UUID_SCHEMA},
                required=("snapshot_id",),
            ),
            _action(
                resource_type,
                "clear_dispatch_error",
                "clear_trigger_dispatch_error",
                {"snapshot_id": UUID_SCHEMA},
            ),
        ),
        named_response=False,
        not_read_first=("delete",),
        filters=filters,
        mutations=tuple(
            replace(mutation, sensitive=Sensitive(f"Changing a {label}"))
            for mutation in mutations
        ),
    )


_RESOURCE_SPECS = (
    _resource(
        "project",
        "Projects",
        rest=Rest("/projects"),
        scope="global",
        default_size=50,
        filters=_filters("name", "display_name"),
        mutations=(
            _mutation(
                "create",
                {"name": _NONEMPTY, "description": _STR},
                required=("name", "description"),
            ),
            _mutation(
                "update",
                {
                    "name": _NONEMPTY,
                    "display_name": _NONEMPTY,
                    "description": _NONEMPTY,
                },
            ),
            _DELETE,
        ),
    ),
    _resource(
        "user",
        "Users",
        rest=Rest("/users"),
        scope="global",
        default_size=50,
        filters=_filters(
            "external_user_id",
            "name",
            "full_name",
            "email",
            "active",
            "email_opted_in",
        ),
    ),
    _resource(
        "stack",
        "Stacks",
        rest=Rest("/stacks"),
        noop_when_empty=("component_updates",),
        scope="global",
        filters=_filters(
            "name", "description", "component_id", "user", "component"
        ),
        mutations=(
            _mutation(
                "create",
                {
                    "name": _NONEMPTY,
                    "components": _stack_components_schema(require_core=True),
                },
                required=("name", "components"),
            ),
            _mutation(
                "update",
                {
                    "name": _NONEMPTY,
                    "description": _NONEMPTY,
                    "component_updates": _stack_components_schema(
                        require_core=False
                    ),
                },
            ),
            _DELETE,
        ),
    ),
    _resource(
        "stack_component",
        "Stack components",
        rest=Rest("/components"),
        noop_when_empty=("configuration",),
        noop_when_false=("disconnect",),
        scope="global",
        filters=_filters(
            "name", "flavor", "type", "connector_id", "stack_id", "user"
        ),
        get_fields=("resource_id", "component_type"),
        mutations=(
            _mutation(
                "create",
                {
                    "name": _NONEMPTY,
                    "flavor": _NONEMPTY,
                    "component_type": COMPONENT_TYPE_SCHEMA,
                    "configuration": _CONFIG_MAP,
                },
                required=("name", "flavor", "component_type", "configuration"),
            ),
            _mutation(
                "update",
                {
                    "name": _NONEMPTY,
                    "configuration": _CONFIG_MAP,
                    "disconnect": _BOOL,
                    "connector_id": UUID_SCHEMA,
                    "connector_resource_id": _STR,
                },
                parents=("component_type",),
                constraints={
                    "allOf": [
                        {
                            "not": {
                                "allOf": [
                                    _required("connector_resource_id"),
                                    {"not": _required("connector_id")},
                                ]
                            }
                        },
                        {
                            "not": {
                                "type": "object",
                                "properties": {"disconnect": {"const": True}},
                                "required": ["disconnect", "connector_id"],
                            }
                        },
                        {
                            "not": {
                                "type": "object",
                                "properties": {"disconnect": {"const": True}},
                                "required": [
                                    "disconnect",
                                    "connector_resource_id",
                                ],
                            }
                        },
                    ]
                },
            ),
            _mutation(
                "delete", parents=("component_type",), payload_required=False
            ),
        ),
    ),
    _resource(
        "flavor",
        "Flavors",
        rest=Rest("/flavors"),
        scope="global",
        filters=_filters(
            "name", "display_name", "type", "integration", "user"
        ),
        mutations=(
            # Declared difference: the fields of the flavor the SDK would build
            # from the class `source` names, which upstream imports.
            _mutation(
                "create",
                {
                    "source": _NONEMPTY,
                    "component_type": COMPONENT_TYPE_SCHEMA,
                    "name": _NONEMPTY,
                    "config_schema": _ANY_MAP,
                    **dict.fromkeys(FLAVOR_TEXT_FIELDS, _STR),
                },
                required=("source", "component_type", "name", "config_schema"),
            ),
            _DELETE,
        ),
    ),
    _resource(
        "service",
        "Services",
        rest=Rest("/services", renames={"service_name": "name"}),
        omitted_fields=("config", "endpoint", "service_source", "status"),
        created_in_active_project=True,
        not_read_first=("update",),
        noop_when_empty=("endpoint", "labels", "status"),
        filters=_filters(
            "type",
            "flavor",
            "user",
            "running",
            "service_name",
            "pipeline_name",
            "pipeline_run_id",
            "pipeline_step_name",
            "model_version_id",
        ),
        mutations=(
            _mutation(
                "create",
                {
                    "config": {
                        "type": "object",
                        "properties": {
                            field: _NONEMPTY
                            if field in {"name", "model_name", "service_name"}
                            else _STR
                            for field in (
                                "name",
                                "description",
                                "pipeline_name",
                                "pipeline_step_name",
                                "model_name",
                                "model_version",
                                "service_name",
                            )
                        },
                        "anyOf": [_required("name"), _required("model_name")],
                        "additionalProperties": False,
                    },
                    "service_type": {
                        "type": "object",
                        "properties": {
                            "type": _NONEMPTY,
                            "flavor": _NONEMPTY,
                            "name": _STR,
                            "description": _STR,
                            "logo_url": _STR,
                        },
                        "required": ["type", "flavor"],
                        "additionalProperties": False,
                    },
                    "model_version_id": UUID_SCHEMA,
                },
                required=("config", "service_type"),
                example={
                    "config": {"name": "<name>"},
                    "service_type": {"type": "<type>", "flavor": "<flavor>"},
                },
            ),
            _mutation(
                "update",
                {
                    "name": _NONEMPTY,
                    "admin_state": {
                        "type": "string",
                        "enum": [
                            "inactive",
                            "active",
                            "pending_startup",
                            "pending_shutdown",
                            "error",
                            "scaled_to_zero",
                        ],
                    },
                    "status": _ANY_MAP,
                    "endpoint": _ANY_MAP,
                    "labels": _STRING_MAP,
                    "prediction_url": _NONEMPTY,
                    "health_check_url": _NONEMPTY,
                    "model_version_id": UUID_SCHEMA,
                },
            ),
            _DELETE,
        ),
    ),
    _resource(
        "pipeline",
        "Pipelines",
        rest=Rest("/pipelines"),
        filters=_filters(
            "name", "latest_run_status", "latest_run_user", "user", "tags"
        ),
        mutations=(_DELETE,),
    ),
    _resource(
        "pipeline_run",
        "Pipeline runs",
        rest=Rest(
            "/runs",
            list_defaults={"sort_by": "desc:created"},
            always={"include_full_metadata": False},
        ),
        actions=(
            _action(
                "pipeline_run",
                "replay",
                "replay_pipeline_run",
                {"run_configuration": _REPLAY_CONFIGURATION},
                returns=True,
                sensitive=Sensitive("Replaying a pipeline run"),
            ),
        ),
        default_size=10,
        filters=_filters(
            "name",
            "pipeline_id",
            "pipeline_name",
            "stack_id",
            "schedule_id",
            "build_id",
            "snapshot_id",
            "code_repository_id",
            "template_id",
            "source_snapshot_id",
            "model_version_id",
            "linked_to_model_version_id",
            "orchestrator_run_id",
            "status",
            "index",
            "start_time",
            "end_time",
            "templatable",
            "tags",
            "user",
            "run_metadata",
            "pipeline",
            "code_repository",
            "model",
            "stack",
            "stack_component",
            "in_progress",
            "triggered_by_step_run_id",
            "triggered_by_deployment_id",
            "trigger_id",
            "parent_run_id",
            "root_runs_only",
        ),
        mutations=(_DELETE,),
    ),
    _resource(
        "run_step",
        "Run steps",
        rest=Rest("/steps", lookup="id"),
        parent=("pipeline_run_id", "pipeline_run"),
        default_size=10,
        filters=_filters(
            "name",
            "cache_key",
            "cache_expires_at",
            "cache_expired",
            "code_hash",
            "status",
            "start_time",
            "end_time",
            "pipeline_run_id",
            "snapshot_id",
            "original_step_run_id",
            "user",
            "model_version_id",
            "model",
            "run_metadata",
            "exclude_retried",
            "version",
        ),
        list_required_filters=("pipeline_run_id",),
        get_fields=("resource_id", "pipeline_run_id"),
    ),
    _resource(
        "snapshot",
        "Snapshots",
        rest=Rest(
            "/pipeline_snapshots",
            list_defaults={"named_only": True},
            lookup="snapshot",
        ),
        named_response=False,
        read_unhydrated=True,
        always_sent=(
            "name",
            "description",
            "replace",
            "add_tags",
            "remove_tags",
        ),
        noop_when_empty=("add_tags", "remove_tags"),
        noop_when_false=("replace",),
        filters=_filters(
            "user",
            "name",
            "named_only",
            "pipeline",
            "stack",
            "build_id",
            "schedule_id",
            "source_snapshot_id",
            "runnable",
            "deployable",
            "deployed",
            "tags",
            "trigger_id",
        ),
        mutations=(
            _mutation(
                "update",
                {
                    "name": _NONEMPTY,
                    "description": _STR,
                    "replace": _BOOL,
                    **_TAG_UPDATES,
                },
            ),
            _DELETE,
        ),
    ),
    _resource(
        "build",
        "Builds",
        rest=Rest("/pipeline_builds", lookup="build"),
        named_response=False,
        filters=_filters(
            "user",
            "pipeline_id",
            "stack_id",
            "container_registry_id",
            "is_local",
            "contains_code",
            "zenml_version",
            "python_version",
            "checksum",
            "stack_checksum",
            "duration",
        ),
        mutations=(_DELETE,),
    ),
    _resource(
        "run_template",
        "Run templates",
        rest=Rest(
            "/run_templates",
            list_defaults={"hidden": False},
            lookup_overrides={"hidden": None},
            name_prefix=False,
        ),
        created_in_active_project=True,
        not_read_first=("update", "delete"),
        always_sent=(
            "name",
            "description",
            "hidden",
            "add_tags",
            "remove_tags",
        ),
        noop_when_empty=("add_tags", "remove_tags"),
        filters=_filters(
            "name",
            "hidden",
            "pipeline_id",
            "build_id",
            "stack_id",
            "code_repository_id",
            "user",
            "pipeline",
            "stack",
        ),
        mutations=(
            _mutation(
                "create",
                {
                    "name": _NONEMPTY,
                    "snapshot_id": UUID_SCHEMA,
                    "description": _STR,
                    "tags": _STRING_LIST,
                },
                required=("name", "snapshot_id"),
            ),
            _mutation(
                "update",
                {
                    "name": _NONEMPTY,
                    "description": _STR,
                    "hidden": _BOOL,
                    **_TAG_UPDATES,
                },
            ),
            _DELETE,
        ),
    ),
    _resource(
        "deployment",
        "Deployments",
        rest=Rest("/deployments", name_prefix=False),
        not_offered={
            "delete": (
                "it removes infrastructure through a deployer built in the client"
            ),
            "provision": (
                "it provisions infrastructure through a deployer built in the client"
            ),
            "deprovision": (
                "it removes infrastructure through a deployer built in the client"
            ),
            "refresh": (
                "it reads the deployment's state through a deployer built in the client"
            ),
        },
        filters=_filters(
            "name",
            "snapshot_id",
            "deployer_id",
            "status",
            "url",
            "user",
            "pipeline",
            "tags",
        ),
    ),
    _resource(
        "schedule",
        "Schedules",
        rest=Rest("/schedules", list_defaults={"is_archived": False}),
        filters=_filters(
            "name",
            "user",
            "pipeline_id",
            "orchestrator_id",
            "active",
            "cron_expression",
            "start_time",
            "end_time",
            "interval_second",
            "catchup",
            "run_once_start_time",
            "is_archived",
        ),
    ),
    _resource(
        "artifact",
        "Artifacts",
        rest=Rest("/artifacts"),
        read_unhydrated=True,
        always_sent=("name", "add_tags", "remove_tags", "has_custom_name"),
        noop_when_empty=("add_tags", "remove_tags"),
        default_size=10,
        filters=_filters("name", "has_custom_name", "user", "tags"),
        mutations=(
            _mutation(
                "update",
                {"name": _NONEMPTY, "has_custom_name": _BOOL, **_TAG_UPDATES},
            ),
            _DELETE,
        ),
    ),
    _resource(
        "artifact_version",
        "Artifact versions",
        rest=Rest(
            "/artifact_versions",
            list_defaults={"only_unused": False},
            # The SDK filters by `artifact`, and a `name` filter replaces it.
            renames={"artifact_id": "artifact", "name": "artifact"},
            lookup="version",
        ),
        named_response=False,
        parent=("artifact_id", "artifact"),
        always_sent=("add_tags", "remove_tags"),
        noop_when_empty=("add_tags", "remove_tags"),
        default_size=10,
        filters=_filters(
            "artifact_id",
            "name",
            "version",
            "version_number",
            "artifact_store_id",
            "type",
            "data_type",
            "uri",
            "materializer",
            "model_version_id",
            "only_unused",
            "has_custom_name",
            "user",
            "model",
            "pipeline_run",
            "run_metadata",
            "tags",
        ),
        list_required_filters=("artifact_id",),
        get_fields=("resource_id", "artifact_id"),
        mutations=(
            _mutation("update", _TAG_UPDATES, parents=("artifact_id",)),
            _mutation(
                "delete",
                {
                    "delete_metadata": _BOOL,
                    "delete_from_artifact_store": _BOOL,
                },
                parents=("artifact_id",),
                payload_required=False,
                constraints={
                    "anyOf": [
                        {
                            "type": "object",
                            "properties": {"delete_metadata": {"const": True}},
                        },
                        {
                            "type": "object",
                            "properties": {
                                "delete_from_artifact_store": {"const": True}
                            },
                            "required": ["delete_from_artifact_store"],
                        },
                    ]
                },
            ),
        ),
    ),
    _resource(
        "model",
        "Models",
        rest=Rest("/models"),
        created_in_active_project=True,
        always_sent=(
            "name",
            "license",
            "description",
            "audience",
            "use_cases",
            "limitations",
            "trade_offs",
            "ethics",
            "add_tags",
            "remove_tags",
            "save_models_to_registry",
        ),
        noop_when_empty=("add_tags", "remove_tags"),
        filters=_filters("name", "user", "tags"),
        mutations=(
            _mutation(
                "create",
                {
                    **_CARD_FIELDS,
                    "tags": _STRING_LIST,
                    "save_models_to_registry": _BOOL,
                },
                required=("name",),
            ),
            _mutation(
                "update",
                {
                    **_CARD_FIELDS,
                    **_TAG_UPDATES,
                    "save_models_to_registry": _BOOL,
                },
            ),
            _DELETE,
        ),
    ),
    _resource(
        "model_version",
        "Model versions",
        rest=Rest(
            "/model_versions",
            list_defaults={"sort_by": "number"},
            renames={"model_id": "model"},
            lookup="model_version",
        ),
        named_response=False,
        parent=("model_id", "model"),
        not_read_first=("update", "delete"),
        always_sent=(
            "stage",
            "force",
            "name",
            "description",
            "add_tags",
            "remove_tags",
        ),
        noop_when_empty=("add_tags", "remove_tags"),
        noop_when_false=("force",),
        filters=_filters(
            "model_id",
            "name",
            "number",
            "stage",
            "run_metadata",
            "user",
            "tags",
        ),
        list_required_filters=("model_id",),
        get_fields=("resource_id", "model_id"),
        mutations=(
            _mutation(
                "create",
                {"name": _NONEMPTY, "description": _STR, "tags": _STRING_LIST},
                parents=("model_id",),
                payload_required=False,
            ),
            _mutation(
                "update",
                {
                    "stage": _MODEL_STAGE,
                    "force": _BOOL,
                    "name": _NONEMPTY,
                    "description": _STR,
                    **_TAG_UPDATES,
                },
                parents=("model_id",),
                # A stage change decides what counts as production and can
                # archive the version that held the stage.
                sensitive=Sensitive(
                    "Changing a model version's stage",
                    when_set=("stage", "force"),
                ),
            ),
            _mutation("delete", parents=("model_id",), payload_required=False),
        ),
    ),
    _resource(
        "tag",
        "Tags",
        rest=Rest("/tags"),
        actions=(
            _action(
                "tag",
                "attach",
                "zen_store.batch_create_tag_resource",
                {
                    "target_id": UUID_SCHEMA,
                    "target_type": TAGGABLE_RESOURCE,
                    "allow_exclusive_replace": _BOOL,
                    "artifact_id": UUID_SCHEMA,
                    "model_id": UUID_SCHEMA,
                },
                required=("target_id", "target_type"),
                returns=True,
            ),
            _action(
                "tag",
                "detach",
                "zen_store.batch_delete_tag_resource",
                {
                    "target_id": UUID_SCHEMA,
                    "target_type": TAGGABLE_RESOURCE,
                    "artifact_id": UUID_SCHEMA,
                    "model_id": UUID_SCHEMA,
                },
                required=("target_id", "target_type"),
            ),
        ),
        scope="global",
        default_size=50,
        filters=_filters(
            "user", "name", "color", "exclusive", "resource_type"
        ),
        mutations=(
            _mutation(
                "create",
                {"name": _NONEMPTY, "exclusive": _BOOL, "color": _COLOR},
                required=("name",),
            ),
            _mutation(
                "update",
                {"name": _NONEMPTY, "exclusive": _BOOL, "color": _COLOR},
            ),
            _DELETE,
        ),
    ),
    _resource(
        "secret",
        "Secret metadata",
        rest=Rest("/secrets"),
        omitted_fields=("value", "values", "secrets", "secret"),
        scope="global",
        default_size=50,
        filters=_filters("name", "private", "user"),
        get_fields=None,
    ),
    _resource(
        "service_connector",
        "Service connectors",
        rest=Rest(
            "/service_connectors",
            always={"expand_secrets": False},
            renames={"labels": "labels_str"},
        ),
        secret_fields={"create": "configuration", "update": "configuration"},
        not_read_first=("update",),
        noop_when_empty=("labels",),
        scope="global",
        filters=_filters(
            "name",
            "connector_type",
            "auth_method",
            "resource_type",
            "resource_id",
            "user",
            "labels",
        ),
        mutations=(
            _mutation(
                "create",
                {
                    "name": _NONEMPTY,
                    "connector_type": _NONEMPTY,
                    "resource_type": _STR,
                    "auth_method": _NONEMPTY,
                    "configuration": _STRING_MAP,
                    "resource_id": _STR,
                    "description": _STR,
                    "expiration_seconds": _NONNEGATIVE_INT,
                    "expires_at": _DATETIME,
                    "expires_skew_tolerance": _NONNEGATIVE_INT,
                    "labels": _STRING_MAP,
                },
                required=("name", "connector_type"),
            ),
            _mutation(
                "update",
                {
                    "name": _NONEMPTY,
                    "auth_method": _NONEMPTY,
                    "resource_type": _STR,
                    "configuration": _STRING_MAP,
                    "resource_id": _STR,
                    "description": _STR,
                    "expiration_seconds": _NONNEGATIVE_INT,
                    "expires_at": _DATETIME,
                    "expires_skew_tolerance": _NONNEGATIVE_INT,
                    "labels": _NULLABLE_STRING_MAP,
                },
            ),
            _DELETE,
        ),
    ),
    _resource(
        "service_connector_type",
        "Service connector types",
        rest=Rest("/service_connector_types", lookup="connector_type"),
        scope="global",
        filters=("connector_type", "resource_type", "auth_method"),
        non_paginated=True,
    ),
    _resource(
        "code_repository",
        "Code repositories",
        rest=Rest("/code_repositories"),
        created_in_active_project=True,
        always_sent=("name", "description", "logo_url"),
        noop_when_empty=("config",),
        filters=_filters("name", "user"),
        mutations=(
            _mutation(
                "create",
                {
                    "name": _NONEMPTY,
                    "source": _NONEMPTY,
                    "config": _ANY_MAP,
                    "description": _STR,
                    "logo_url": _STR,
                },
                required=("name", "source", "config"),
            ),
            _mutation(
                "update",
                {
                    "name": _NONEMPTY,
                    "description": _STR,
                    "logo_url": _STR,
                    "config": _CONFIG_MAP,
                },
            ),
            _DELETE,
        ),
    ),
    _resource(
        "webhook",
        "Webhooks",
        rest=Rest("/webhooks"),
        actions=(
            _action(
                "webhook",
                "rotate_secret",
                "rotate_webhook_secret",
                {"secret": _NONEMPTY},
                returns=True,
            ),
        ),
        secret_fields={"create": "secret", "rotate_secret": "secret"},
        created_in_active_project=True,
        not_read_first=("update",),
        always_sent=("name", "active"),
        filters=_filters("name", "user", "webhook_type", "active"),
        mutations=(
            _mutation(
                "create",
                {
                    "name": _NONEMPTY,
                    "webhook_type": _NONEMPTY,
                    "active": _BOOL,
                    "secret": _NONEMPTY,
                },
                required=("name", "webhook_type"),
            ),
            _mutation(
                "update",
                {"name": _NONEMPTY, "active": _BOOL},
                # ZenML dispatches a webhook's events to its triggers, which
                # start runs, only while the webhook is on.
                sensitive=Sensitive(
                    "Switching a webhook on", when_set=("active",)
                ),
            ),
            _DELETE,
        ),
    ),
    _trigger(
        "schedule_trigger",
        "Schedule triggers",
        flavor="native schedule",
        kind="schedule",
        filters=_filters(
            "user",
            "name",
            "active",
            "concurrency",
            "is_archived",
            "next_occurrence",
            "pipeline_id",
            "snapshot_id",
        ),
        mutations=(
            _mutation(
                "create",
                _SCHEDULE_TRIGGER_FIELDS,
                required=("name",),
                constraints={
                    "oneOf": [
                        _only(
                            ("cron_expression",),
                            "interval",
                            "run_once_start_time",
                        ),
                        _only(
                            ("interval", "start_time"),
                            "cron_expression",
                            "run_once_start_time",
                        ),
                        _only(
                            ("run_once_start_time",),
                            "cron_expression",
                            "interval",
                        ),
                    ]
                },
                example={"name": "<name>", "cron_expression": "0 * * * *"},
            ),
            _mutation(
                "update",
                _SCHEDULE_TRIGGER_FIELDS,
                constraints={
                    "not": {
                        "anyOf": [
                            _required(*pair)
                            for pair in combinations(
                                (
                                    "cron_expression",
                                    "interval",
                                    "run_once_start_time",
                                ),
                                2,
                            )
                        ]
                    }
                },
            ),
            _DELETE,
        ),
    ),
    _trigger(
        "platform_event_trigger",
        "Platform event triggers",
        flavor="platform event",
        kind="platform_event",
        filters=_filters(
            "user",
            "name",
            "active",
            "concurrency",
            "is_archived",
            "pipeline_id",
            "snapshot_id",
        ),
        mutations=(
            _mutation(
                "create",
                _EVENT_TRIGGER_FIELDS,
                required=("name", "source_type", "source_id", "target_events"),
            ),
            _mutation("update", _EVENT_TRIGGER_FIELDS),
            _DELETE,
        ),
    ),
    _trigger(
        "webhook_trigger",
        "Webhook triggers",
        flavor="webhook",
        kind="webhook",
        filters=_filters(
            "user",
            "name",
            "active",
            "concurrency",
            "is_archived",
            "webhook_id",
            "pipeline_id",
            "snapshot_id",
        ),
        mutations=(
            _mutation(
                "create",
                {
                    **_TRIGGER_COMMON,
                    "webhook_id": UUID_SCHEMA,
                    "configuration": _ANY_MAP,
                },
                required=("name", "webhook_id", "configuration"),
            ),
            _mutation(
                "update", {**_TRIGGER_COMMON, "configuration": _ANY_MAP}
            ),
            _DELETE,
        ),
    ),
    _resource(
        "resource_request",
        "Resource requests",
        rest=Rest("/resource_requests", lookup="id"),
        named_response=False,
        scope="global",
        filters=_filters(
            "scope_user",
            "user",
            "preemptible",
            "component_id",
            "step_run_id",
            "preemption_initiated_by_id",
            "status",
            "pipeline_run_id",
        ),
    ),
    _resource(
        "run_wait_condition",
        "Run wait conditions",
        rest=Rest(
            "/run_wait_conditions", list_defaults={"sort_by": "desc:created"}
        ),
        actions=(
            _action(
                "run_wait_condition",
                "resolve",
                "resolve_run_wait_condition",
                {
                    "resolution": {
                        "type": "string",
                        "enum": ["CONTINUE", "ABORT"],
                    },
                    "result": {},
                },
                required=("resolution",),
                returns=True,
                sensitive=Sensitive("Resuming or stopping a paused run"),
            ),
        ),
        default_size=10,
        filters=_filters(
            "name",
            "resolved_by",
            "resolved_at",
            "resolution",
            "pipeline_run",
            "user",
            "run_metadata",
            "status",
            "type",
        ),
        get_fields=None,
    ),
    _resource(
        "hook_invocation",
        "Hook invocations",
        rest=Rest("/hook_invocations", lookup="id"),
        named_response=False,
        not_read_first=("delete",),
        default_size=10,
        filters=_filters(
            "pipeline_run_id",
            "step_run_id",
            "hook_type",
            "name",
            "status",
            "start_time",
            "end_time",
            "user",
        ),
        mutations=(_DELETE,),
    ),
)

RESOURCE_REGISTRY: Mapping[str, ResourceSpec] = MappingProxyType(
    {spec.resource_type: spec for spec in _RESOURCE_SPECS}
)


def get_resource_spec(resource_type: str) -> ResourceSpec:
    """Return the exact resource spec; aliases are deliberately unsupported.

    Args:
        resource_type: The type's catalog name.

    Returns:
        The type's record.

    Raises:
        ZenMLBadRequest: When the type is not in the catalog.
    """
    try:
        return RESOURCE_REGISTRY[resource_type]
    except KeyError as error:
        allowed = ", ".join(RESOURCE_REGISTRY)
        raise ZenMLBadRequest(
            f"Unknown resource type {resource_type!r}; allowed resource types: {allowed}"
        ) from error
