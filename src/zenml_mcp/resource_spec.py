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
"""The record each resource type of the generic tools is described by.

The record drives the validation of filters, payload schemas and the input
of an operation or an action.

Ported from mcp-zenml's `zenml_resource_registry.py` (commit 3de0643). The
records themselves are in `resource_catalog.py`.
"""

from __future__ import annotations

import dataclasses
import json
import re
import uuid
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any, Literal, cast

from zenml_mcp.client import ZenMLBadRequest


def _no_entries() -> Mapping[str, Any]:
    """An empty read-only mapping, as a dataclass field's default.

    Python 3.11 refuses an unhashable default such as a `MappingProxyType`.

    Returns:
        A new empty mapping.
    """
    return MappingProxyType({})


Mutation = Literal["create", "update", "delete"]
Operation = Literal["list", "get", "create", "update", "delete"]
ScopeKind = Literal["global", "project"]
Lookup = Literal[
    "name",
    "id",
    "build",
    "snapshot",
    "version",
    "model_version",
    "connector_type",
]

MAX_PAGE_SIZE = 200
DATETIME_FILTERS = frozenset(
    {
        "created",
        "updated",
        "start_time",
        "end_time",
        "cache_expires_at",
        "next_occurrence",
        "resolved_at",
        "run_once_start_time",
    }
)

BOOLEAN_FILTERS = frozenset(
    {
        "active",
        "cache_expired",
        "catchup",
        "contains_code",
        "deployable",
        "deployed",
        "email_opted_in",
        "exclude_retried",
        "exclusive",
        "has_custom_name",
        "hidden",
        "in_progress",
        "is_archived",
        "is_local",
        "named_only",
        "only_unused",
        "preemptible",
        "private",
        "root_runs_only",
        "runnable",
        "running",
        "templatable",
    }
)
INTEGER_FILTERS = frozenset(
    {"duration", "index", "number", "version", "version_number"}
)
NUMBER_FILTERS = frozenset({"interval_second"})
_SCALAR_STRING_FILTERS = frozenset(
    {
        ("artifact_version", "name"),
        ("pipeline", "latest_run_user"),
        ("service_connector", "resource_id"),
        ("service_connector", "resource_type"),
        ("service_connector_type", "auth_method"),
        ("service_connector_type", "connector_type"),
        ("service_connector_type", "resource_type"),
    }
)
_UUID_ONLY_FILTERS = frozenset({("snapshot", "trigger_id")})

# Only the trigger types have a `concurrency` filter.
CONCURRENCY = ("skip", "submit")
MODEL_STAGES = ("none", "staging", "production", "archived")

_EXECUTION_STATUSES = (
    "initializing",
    "provisioning",
    "queued",
    "running",
    "failed",
    "completed",
    "cached",
    "skipped",
    "retrying",
    "retried",
    "cancelling",
    "cancelled",
    "paused",
    "resuming",
    "stopped",
    "stopping",
)

_ENUM_FILTERS: Mapping[tuple[str, str], tuple[str, ...]] = MappingProxyType(
    {
        ("pipeline", "latest_run_status"): _EXECUTION_STATUSES,
        ("pipeline_run", "status"): _EXECUTION_STATUSES,
        ("run_step", "status"): _EXECUTION_STATUSES,
        ("hook_invocation", "status"): _EXECUTION_STATUSES,
        ("deployment", "status"): (
            "unknown",
            "pending",
            "running",
            "absent",
            "error",
        ),
        ("resource_request", "status"): (
            "pending",
            "allocated",
            "preempting",
            "preempted",
            "cancelled",
            "rejected",
            "released",
        ),
        ("run_wait_condition", "status"): ("pending", "resolved"),
        ("model_version", "stage"): (*MODEL_STAGES, "latest"),
        ("tag", "color"): (
            "grey",
            "purple",
            "red",
            "green",
            "yellow",
            "orange",
            "lime",
            "teal",
            "turquoise",
            "magenta",
            "blue",
        ),
        ("tag", "resource_type"): (
            "artifact",
            "artifact_version",
            "model",
            "model_version",
            "pipeline",
            "pipeline_run",
            "run_template",
            "pipeline_snapshot",
            "deployment",
        ),
    }
)


def _enum_values(resource_type: str, field: str) -> tuple[str, ...] | None:
    if field == "concurrency":
        return CONCURRENCY
    return _ENUM_FILTERS.get((resource_type, field))


def _scalar_or_array_schema(scalar: dict[str, Any]) -> dict[str, Any]:
    """Build the JSON shape used by ZenML scalar-or-list filter parameters.

    Args:
        scalar: The schema of one value.

    Returns:
        A schema that takes that value alone or a non-empty list of them.
    """
    return {
        "anyOf": [
            scalar,
            {"type": "array", "items": scalar, "minItems": 1},
        ]
    }


def _enum_filter_schema(values: tuple[str, ...]) -> dict[str, Any]:
    scalar = {"type": "string", "enum": list(values)}
    schema = _scalar_or_array_schema(scalar)
    alternatives = "|".join(re.escape(value) for value in values)
    schema["anyOf"].append(
        {
            "type": "string",
            "pattern": (
                rf"^(?:(?:equals|notequals):(?:{alternatives})|"
                rf'(?:oneof|notoneof):\s*\[\s*"(?:{alternatives})"'
                rf'(?:\s*,\s*"(?:{alternatives})")*\s*\])$'
            ),
        }
    )
    return schema


def filter_schema(resource_type: str, field: str) -> dict[str, Any]:
    """Return the public JSON schema for one allowlisted filter.

    Args:
        resource_type: The catalogued type the filter belongs to.
        field: The filter's name.

    Returns:
        The filter's JSON schema.
    """
    if field == "logical_operator":
        return {"type": "string", "enum": ["and", "or"]}
    if field == "sort_by":
        return {"type": "string", "minLength": 1}
    if field == "labels":
        return {
            "type": "object",
            "additionalProperties": {
                "anyOf": [{"type": "string"}, {"type": "null"}]
            },
        }
    if (resource_type, field) in _UUID_ONLY_FILTERS:
        return {"type": "string", "format": "uuid"}
    if (resource_type, field) in _SCALAR_STRING_FILTERS:
        return {"type": "string", "minLength": 1}
    if field in BOOLEAN_FILTERS:
        return {"type": "boolean"}
    if field in INTEGER_FILTERS:
        return _scalar_or_array_schema(
            {
                "anyOf": [
                    {"type": "integer"},
                    {"type": "string", "minLength": 1},
                ]
            }
        )
    if field in NUMBER_FILTERS:
        return _scalar_or_array_schema(
            {
                "anyOf": [
                    {"type": "number"},
                    {"type": "string", "minLength": 1},
                ]
            }
        )
    enum_values = _enum_values(resource_type, field)
    if enum_values is not None:
        return _enum_filter_schema(enum_values)
    return _scalar_or_array_schema({"type": "string", "minLength": 1})


def _filter_operands(value: Any) -> list[Any]:
    if not isinstance(value, str):
        return value if isinstance(value, list) else [value]
    operation, separator, operand = value.partition(":")
    if not separator:
        return [value]
    if operation in {"oneof", "notoneof"}:
        try:
            decoded = json.loads(operand)
        except json.JSONDecodeError:
            return []
        return decoded if isinstance(decoded, list) else []
    if operation in {"equals", "notequals"}:
        return [operand]
    return [value]


def validate_filter_value(resource_type: str, field: str, value: Any) -> None:
    """Validate against the same static types exposed in discovery.

    Args:
        resource_type: The catalogued type the filter belongs to.
        field: The filter's name.
        value: The filter's value, which may carry an operator prefix.

    Raises:
        ZenMLBadRequest: When the value doesn't fit the filter's type.
    """
    if field == "logical_operator":
        valid = isinstance(value, str) and value in {"and", "or"}
    elif field == "sort_by":
        valid = isinstance(value, str) and bool(value)
    elif field == "labels":
        valid = isinstance(value, dict) and all(
            isinstance(key, str) and (item is None or isinstance(item, str))
            for key, item in value.items()
        )
    elif (resource_type, field) in _UUID_ONLY_FILTERS:
        try:
            valid = (
                isinstance(value, str)
                and str(uuid.UUID(value)) == value.lower()
            )
        except (AttributeError, ValueError):
            valid = False
    elif (resource_type, field) in _SCALAR_STRING_FILTERS:
        valid = isinstance(value, str) and bool(value)
    elif field in BOOLEAN_FILTERS:
        valid = isinstance(value, bool)
    else:
        values = _filter_operands(value)
        valid = bool(values)
        if field in INTEGER_FILTERS:
            valid = valid and all(
                (isinstance(item, int) and not isinstance(item, bool))
                or (isinstance(item, str) and bool(item))
                for item in values
            )
        elif field in NUMBER_FILTERS:
            valid = valid and all(
                (isinstance(item, (int, float)) and not isinstance(item, bool))
                or (isinstance(item, str) and bool(item))
                for item in values
            )
        else:
            enum_values = _enum_values(resource_type, field)
            valid = valid and all(
                isinstance(item, str)
                and bool(item)
                and (enum_values is None or item in enum_values)
                for item in values
            )
    if not valid:
        raise ZenMLBadRequest(
            f"Invalid value for {resource_type!r} filter {field!r}"
        )


def matches_schema(value: Any, schema: Mapping[str, Any]) -> bool:
    """Whether a value fits a JSON schema.

    Only the keywords the catalog's schemas use are checked; any other
    keyword is ignored.

    Args:
        value: The value to check.
        schema: The JSON schema.

    Returns:
        Whether the value fits.
    """
    if "const" in schema and value != schema["const"]:
        return False
    alternatives = schema.get("anyOf")
    if alternatives and not any(
        matches_schema(value, alternative) for alternative in alternatives
    ):
        return False
    alternatives = schema.get("oneOf")
    if (
        alternatives
        and sum(
            matches_schema(value, alternative) for alternative in alternatives
        )
        != 1
    ):
        return False
    excluded = schema.get("not")
    if excluded and matches_schema(value, excluded):
        return False
    requirements = schema.get("allOf")
    if requirements and not all(
        matches_schema(value, requirement) for requirement in requirements
    ):
        return False
    expected = schema.get("type")
    if expected == "null":
        return value is None
    if expected == "string":
        if not isinstance(value, str):
            return False
        if len(value) < schema.get("minLength", 0):
            return False
        if "enum" in schema and value not in schema["enum"]:
            return False
        if (
            "pattern" in schema
            and re.fullmatch(schema["pattern"], value) is None
        ):
            return False
        if schema.get("format") == "uuid":
            try:
                return str(uuid.UUID(value)) == value.lower()
            except ValueError:
                return False
        if schema.get("format") == "date-time":
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return False
        return True
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return (
            isinstance(value, int)
            and not isinstance(value, bool)
            and value >= schema.get("minimum", value)
            and value <= schema.get("maximum", value)
        )
    if expected == "number":
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and value >= schema.get("minimum", value)
            and value <= schema.get("maximum", value)
        )
    if expected == "array":
        return (
            isinstance(value, list)
            and len(value) >= schema.get("minItems", 0)
            and all(
                matches_schema(item, schema.get("items", {})) for item in value
            )
        )
    if expected == "object":
        if not isinstance(value, dict):
            return False
        if len(value) < schema.get("minProperties", 0):
            return False
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False and set(value) - set(
            properties
        ):
            return False
        if not set(schema.get("required", ())) <= set(value):
            return False
        additional = schema.get("additionalProperties")
        return all(
            matches_schema(
                item,
                properties.get(
                    key, additional if isinstance(additional, dict) else {}
                ),
            )
            for key, item in value.items()
        )
    return True


def validate_mutation_payload(
    spec: ResourceSpec,
    operation: str,
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Validate a mutation payload against its advertised operation schema.

    Args:
        spec: The resource type's record.
        operation: `create`, `update` or `delete`.
        payload: The payload, if any.

    Returns:
        A copy of the payload, empty when none was given.

    Raises:
        ZenMLBadRequest: When the payload is missing, has a field the
            operation doesn't take or lacks one it requires, has a value
            that doesn't fit, or is an update that changes nothing.
    """
    resource_type = spec.resource_type
    mutation = spec.mutation(operation)
    value = dict(payload or {})
    if mutation.payload_required and payload is None:
        raise ZenMLBadRequest(
            f"{resource_type!r} {operation} requires payload"
        )
    unsupported = sorted(set(value) - set(mutation.payload_properties))
    if unsupported:
        allowed = ", ".join(mutation.payload_properties) or "none"
        raise ZenMLBadRequest(
            f"Unsupported fields for {resource_type!r} {operation}: "
            f"{', '.join(unsupported)}. Allowed fields: {allowed}"
        )
    missing = sorted(set(mutation.required_payload) - set(value))
    if missing:
        raise ZenMLBadRequest(
            f"{resource_type!r} {operation} requires fields: {', '.join(missing)}"
        )
    for field, item in value.items():
        if not matches_schema(item, mutation.payload_properties[field]):
            raise ZenMLBadRequest(
                f"Invalid value for {resource_type!r} {operation} field {field!r}"
            )
    if not matches_schema(value, mutation.payload_schema(spec)):
        raise ZenMLBadRequest(
            f"Invalid payload for {resource_type!r} {operation}"
        )
    if operation == "update":
        effective_fields = {
            field
            for field, item in value.items()
            if not (field in spec.noop_when_empty and not item)
            and not (field in spec.noop_when_false and item is False)
        }
        if not effective_fields:
            raise ZenMLBadRequest(
                f"{resource_type!r} update requires at least one effective field"
            )
    return value


@dataclass(frozen=True)
class OperationSpec:
    """One public generic operation with a bounded input contract."""

    resource_type: str
    fields: tuple[str, ...]
    required_fields: tuple[str, ...] = ()
    filter_fields: tuple[str, ...] = ()
    required_filter_fields: tuple[str, ...] = ()
    description: str = ""
    property_schemas: Mapping[str, dict[str, Any]] | None = None

    def schema(self) -> dict[str, Any]:
        """The operation's input as a JSON schema.

        Returns:
            An object schema that takes no field beyond the operation's.
        """
        properties: dict[str, Any] = {
            "resource_type": {"type": "string", "const": self.resource_type},
            **{
                field: {"type": "string"}
                for field in self.fields
                if field not in {"page", "size"}
            },
        }
        if self.property_schemas:
            properties.update(self.property_schemas)
        if "page" in self.fields:
            properties["page"] = {"type": "integer", "minimum": 1}
        if "size" in self.fields:
            properties["size"] = {
                "type": "integer",
                "minimum": 1,
                "maximum": MAX_PAGE_SIZE,
            }
        if "filters" in self.fields:
            properties["filters"] = {
                "type": "object",
                "properties": {
                    field: filter_schema(self.resource_type, field)
                    for field in self.filter_fields
                },
                "required": list(self.required_filter_fields),
                "additionalProperties": False,
            }
        return {
            "type": "object",
            "properties": properties,
            "required": ["resource_type", *self.required_fields],
            "additionalProperties": False,
        }


@dataclass(frozen=True)
class Rest:
    """How the SDK reaches one resource type over REST.

    As of ZenML 0.97.0, `client.py` and `rest_zen_store.py`.
    """

    route: str
    # What the SDK's list method sends when the caller leaves a filter out.
    list_defaults: Mapping[str, Any] = dataclasses.field(
        default_factory=_no_entries
    )
    # What the SDK's get method changes in `list_defaults` when it searches.
    lookup_overrides: Mapping[str, Any] = dataclasses.field(
        default_factory=_no_entries
    )
    # Sent with every request for the type.
    always: Mapping[str, Any] = dataclasses.field(default_factory=_no_entries)
    # Filters the SDK sends under another name, applied in order.
    renames: Mapping[str, str] = dataclasses.field(default_factory=_no_entries)
    lookup: Lookup = "name"
    name_prefix: bool = True


@dataclass(frozen=True)
class ResourceSpec:
    """Everything this server knows about one ZenML resource type.

    That is the public contract mcp-zenml's registry gives it, and what the
    SDK sends for it.
    """

    resource_type: str
    description: str
    rest: Rest
    scope: ScopeKind
    default_size: int
    list_filters: tuple[str, ...]
    list_required_filters: tuple[str, ...]
    get_fields: tuple[str, ...] | None
    get_required: tuple[str, ...] = ("resource_id",)
    non_paginated: bool = False
    mutations: Mapping[str, MutationSpec] = dataclasses.field(
        default_factory=_no_entries
    )
    actions: Mapping[str, ActionSpec] = dataclasses.field(
        default_factory=_no_entries
    )
    # Upstream operations and actions this server leaves out, and why.
    not_offered: Mapping[str, str] = dataclasses.field(
        default_factory=_no_entries
    )
    # The field a write carries its secret in. With a secret page, a tool call
    # offers the write only through the page, which asks for that field.
    secret_fields: Mapping[str, str] = dataclasses.field(
        default_factory=_no_entries
    )
    noop_when_empty: frozenset[str] = frozenset()
    noop_when_false: frozenset[str] = frozenset()
    # The parent a get and a write name: the argument, and the response's key.
    parent: tuple[str, str] | None = None
    # Whether the SDK's response model requires a `name` next to the `id`
    # (ZenML 0.97.0 `zenml.models`).
    named_response: bool = True
    omitted_fields: frozenset[str] = frozenset()
    # The SDK creates it only in its active project, so upstream refuses any
    # other project.
    created_in_active_project: bool = False
    # Writes the SDK sends without the usual read of the entity first: by id
    # alone, or, for a connector update, after a read of its own.
    not_read_first: frozenset[str] = frozenset()
    read_unhydrated: bool = False
    # Update fields the SDK always sends, as null when the caller leaves one
    # out. ZenML tells a field set to null from a field left out.
    always_sent: tuple[str, ...] = ()

    @property
    def operations(self) -> tuple[Operation, ...]:
        """The operations offered for the type.

        Returns:
            `list`, `get` when the type can be read by id, then its writes.
        """
        reads: tuple[Operation, ...] = (
            ("list", "get") if self.get_fields is not None else ("list",)
        )
        return (
            *reads,
            *(cast(Operation, operation) for operation in self.mutations),
        )

    @property
    def trigger(self) -> tuple[str, str] | None:
        """The `type` and `flavor` the SDK tells this trigger type apart by.

        The trigger types share one route, so these pick the type on it.

        Returns:
            The pair, or None when the type is not a trigger.
        """
        if self.rest.route != "/triggers":
            return None
        return self.rest.list_defaults["type"], self.rest.list_defaults[
            "flavor"
        ]

    def mutation(self, operation: str) -> MutationSpec:
        """The create, update or delete this server offers for the type.

        Args:
            operation: The operation's name.

        Returns:
            The operation's contract.

        Raises:
            ZenMLBadRequest: When the type doesn't offer the operation.
        """  # noqa: DOC503
        found = self.mutations.get(operation)
        if found is None:
            raise self._unsupported(operation)
        return found

    def action(self, name: str) -> ActionSpec:
        """One exact action, rejecting aliases and inferred methods.

        Args:
            name: The action's name.

        Returns:
            The action's contract.

        Raises:
            ZenMLBadRequest: When the type doesn't offer the action, with the
                reason when this server leaves it out on purpose.
        """  # noqa: DOC503
        found = self.actions.get(name)
        if found is not None:
            return found
        left_out = self._left_out(name)
        if left_out:
            raise left_out
        supported = sorted(self.actions)
        suffix = (
            f"; supported actions: {', '.join(supported)}" if supported else ""
        )
        raise ZenMLBadRequest(
            f"Unsupported action {name!r} for {self.resource_type!r}{suffix}"
        )

    def _left_out(self, name: str) -> ZenMLBadRequest | None:
        why = self.not_offered.get(name)
        if not why:
            return None
        return ZenMLBadRequest(
            f"This server does not offer {name} for {self.resource_type!r}: {why}."
        )

    def _unsupported(self, operation: str) -> ZenMLBadRequest:
        return self._left_out(operation) or ZenMLBadRequest(
            f"Unsupported operation {operation!r} for {self.resource_type!r}; "
            f"supported operations: {', '.join(self.operations)}"
        )

    def operation_spec(self, operation: str) -> OperationSpec:
        """The input contract of one operation on the type.

        Args:
            operation: The operation's name.

        Returns:
            The operation's contract.

        Raises:
            ZenMLBadRequest: When the type doesn't offer the operation.
        """  # noqa: DOC503
        scope_fields = ("project_id",) if self.scope == "project" else ()
        if operation == "list":
            return OperationSpec(
                resource_type=self.resource_type,
                fields=("page", "size", *scope_fields, "filters"),
                required_fields=("filters",)
                if self.list_required_filters
                else (),
                filter_fields=self.list_filters,
                required_filter_fields=self.list_required_filters,
                description=f"List {self.description.lower()} with bounded filters.",
                property_schemas=MappingProxyType(
                    {"project_id": deepcopy(UUID_SCHEMA)}
                )
                if scope_fields
                else None,
            )
        if operation == "get" and self.get_fields is not None:
            property_schemas: dict[str, dict[str, Any]] = {
                field: deepcopy(UUID_SCHEMA)
                for field in (*scope_fields, *self.get_fields)
                if field
                in {"project_id", "artifact_id", "model_id", "pipeline_run_id"}
            }
            if self.resource_type == "stack_component":
                property_schemas["component_type"] = deepcopy(
                    COMPONENT_TYPE_SCHEMA
                )
            property_schemas["hydrate"] = {"type": "boolean"}
            return OperationSpec(
                resource_type=self.resource_type,
                fields=(*scope_fields, *self.get_fields, "hydrate"),
                required_fields=self.get_required,
                description=f"Get one {self.description.lower()} by an identifier.",
                property_schemas=MappingProxyType(property_schemas),
            )
        if operation in self.mutations:
            return self.mutations[operation].operation_spec(self)
        raise self._unsupported(operation)


@dataclass(frozen=True)
class MutationSpec:
    """Static contract for one ordinary create, update, or delete operation."""

    operation: Mutation
    payload_properties: Mapping[str, dict[str, Any]] = dataclasses.field(
        default_factory=_no_entries
    )
    required_payload: tuple[str, ...] = ()
    parent_fields: tuple[str, ...] = ()
    payload_required: bool = False
    description: str = ""
    payload_constraints: Mapping[str, Any] = dataclasses.field(
        default_factory=_no_entries
    )
    example_payload: Mapping[str, Any] | None = None

    def payload_schema(self, resource: ResourceSpec) -> dict[str, Any]:
        """The operation's payload as a JSON schema.

        An update must change something: it takes at least one field, a field
        that is a no-op when empty can't be empty, and a field that is a no-op
        when false counts only when true.

        Args:
            resource: The resource type's record.

        Returns:
            An object schema that takes no field beyond the payload's.
        """
        properties = deepcopy(dict(self.payload_properties))
        if self.operation == "update":
            for name in resource.noop_when_empty:
                emptied = properties[name]
                if emptied.get("type") == "array":
                    emptied["minItems"] = 1
                elif emptied.get("type") == "object":
                    emptied["minProperties"] = 1

        schema: dict[str, Any] = {
            "type": "object",
            "properties": properties,
            "required": list(self.required_payload),
            "additionalProperties": False,
            **deepcopy(dict(self.payload_constraints)),
        }
        if self.operation == "update":
            schema["minProperties"] = 1
            if resource.noop_when_false:
                schema["anyOf"] = [
                    {
                        "type": "object",
                        "properties": {name: {"const": True}},
                        "required": [name],
                    }
                    if name in resource.noop_when_false
                    else {"type": "object", "required": [name]}
                    for name in properties
                ]
        return schema

    def operation_spec(self, resource: ResourceSpec) -> OperationSpec:
        """The operation's input contract.

        Args:
            resource: The resource type's record.

        Returns:
            The contract, with the ids and the payload the operation takes.
        """
        fields: list[str] = []
        required: list[str] = []
        properties: dict[str, dict[str, Any]] = {}
        if self.operation != "create":
            fields.append("resource_id")
            required.append("resource_id")
            properties["resource_id"] = {"type": "string", "format": "uuid"}
        if resource.scope == "project":
            fields.append("project_id")
            required.append("project_id")
            properties["project_id"] = {"type": "string", "format": "uuid"}
        for field in self.parent_fields:
            fields.append(field)
            required.append(field)
            properties[field] = (
                COMPONENT_TYPE_SCHEMA
                if field == "component_type"
                else {"type": "string", "format": "uuid"}
            )
        if self.payload_properties or self.payload_required:
            fields.append("payload")
            if self.payload_required:
                required.append("payload")
            properties["payload"] = self.payload_schema(resource)
        return OperationSpec(
            resource_type=resource.resource_type,
            fields=tuple(fields),
            required_fields=tuple(required),
            description=self.description
            or f"{self.operation.title()} {resource.description.lower()}.",
            property_schemas=MappingProxyType(properties),
        )


UUID_SCHEMA = {"type": "string", "format": "uuid"}
COMPONENT_TYPE_SCHEMA = {
    "type": "string",
    "enum": [
        "alerter",
        "annotator",
        "artifact_store",
        "container_registry",
        "data_validator",
        "deployer",
        "experiment_tracker",
        "feature_store",
        "image_builder",
        "log_store",
        "model_deployer",
        "model_registry",
        "orchestrator",
        "sandbox",
        "step_operator",
    ],
}

TAGGABLE_RESOURCE = {
    "type": "string",
    "enum": list(_ENUM_FILTERS[("tag", "resource_type")]),
}


def catalog_type(zenml_type: str) -> str:
    """The catalog's type for one a tag or a platform event names.

    ZenML calls the snapshot type `pipeline_snapshot` there.

    Args:
        zenml_type: The type as ZenML names it.

    Returns:
        The catalog's name for it.
    """
    return "snapshot" if zenml_type == "pipeline_snapshot" else zenml_type


@dataclass(frozen=True)
class ActionSpec:
    """Static contract for one explicitly supported resource action."""

    resource_type: str
    action: str
    sdk_method: str
    payload_properties: Mapping[str, dict[str, Any]] = dataclasses.field(
        default_factory=_no_entries
    )
    required_payload: tuple[str, ...] = ()
    prerequisites: tuple[str, ...] = ()
    # The SDK method returns what ZenML answered; the others return nothing.
    returns: bool = False

    def schema(self) -> dict[str, Any]:
        """The action's input as a JSON schema.

        A tag action names exactly the ids its target type needs.

        Returns:
            An object schema that takes no field beyond the action's.
        """
        payload_schema: dict[str, Any] = {
            "type": "object",
            "properties": dict(self.payload_properties),
            "required": list(self.required_payload),
            "additionalProperties": False,
        }
        if self.resource_type == "tag":
            payload_schema["oneOf"] = [
                {
                    "properties": {
                        "target_type": {"const": "artifact_version"}
                    },
                    "required": ["target_type", "artifact_id"],
                    "not": {"required": ["model_id"]},
                },
                {
                    "properties": {"target_type": {"const": "model_version"}},
                    "required": ["target_type", "model_id"],
                    "not": {"required": ["artifact_id"]},
                },
                {
                    "properties": {
                        "target_type": {
                            "enum": [
                                value
                                for value in TAGGABLE_RESOURCE["enum"]
                                if value
                                not in {"artifact_version", "model_version"}
                            ]
                        }
                    },
                    "required": ["target_type"],
                    "not": {
                        "anyOf": [
                            {"required": ["artifact_id"]},
                            {"required": ["model_id"]},
                        ]
                    },
                },
            ]
        properties: dict[str, Any] = {
            "resource_type": {"type": "string", "const": self.resource_type},
            "action": {"type": "string", "const": self.action},
            "resource_id": {"type": "string", "format": "uuid"},
            "payload": payload_schema,
        }
        required = ["resource_type", "action", "resource_id"]
        if self.required_payload:
            required.append("payload")
        properties["project_id"] = {"type": "string", "format": "uuid"}
        required.append("project_id")
        return {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }


def validate_action_payload(
    spec: ActionSpec, payload: Mapping[str, Any] | None
) -> dict[str, Any]:
    """Validate action input before any request is sent.

    Args:
        spec: The action's contract.
        payload: The payload, if any.

    Returns:
        A copy of the payload, empty when none was given.

    Raises:
        ZenMLBadRequest: When the payload has a field the action doesn't
            take, lacks one it requires, or has a value that doesn't fit.
    """
    resource_type, action = spec.resource_type, spec.action
    value = dict(payload or {})
    unsupported = sorted(set(value) - set(spec.payload_properties))
    if unsupported:
        allowed = ", ".join(spec.payload_properties) or "none"
        raise ZenMLBadRequest(
            f"Unsupported fields for {resource_type!r} {action}: "
            f"{', '.join(unsupported)}. Allowed fields: {allowed}"
        )
    missing = sorted(set(spec.required_payload) - set(value))
    if missing:
        raise ZenMLBadRequest(
            f"{resource_type!r} {action} requires fields: {', '.join(missing)}"
        )
    for field, item in value.items():
        if not matches_schema(item, spec.payload_properties[field]):
            raise ZenMLBadRequest(
                f"Invalid value for {resource_type!r} {action} field {field!r}"
            )
    return value


# ZenML's stack component types (zenml.enums.StackComponentType).
COMPONENT_TYPES = (
    "orchestrator",
    "artifact_store",
    "container_registry",
    "step_operator",
    "experiment_tracker",
    "image_builder",
    "model_registry",
    "model_deployer",
    "deployer",
    "alerter",
    "annotator",
    "data_validator",
    "feature_store",
    "log_store",
    "sandbox",
)
