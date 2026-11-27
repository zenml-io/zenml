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
"""The ZenML SDK's service connectors, as this server writes them.

These are the SDK's `create_service_connector` and `update_service_connector`
bodies, and the configuring both do from the connector type's specification.
A connector type is the one ZenML serves, as the SDK reads it where no
connector package is installed.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from contextlib import suppress
from datetime import datetime
from typing import Any

from zenml_mcp.call import Asked
from zenml_mcp.client import ZenMLBadRequest, ZenMLUnsupported
from zenml_mcp.common import body_of, field_of, meta_of, segment
from zenml_mcp.credentials import (
    credentials_off_schema,
    refuse_keys,
)
from zenml_mcp.resources import (
    WriteRequest,
    with_remote_connector_type,
)


def _sdk_datetime(value: Any) -> Any:
    """A time as the SDK sends it once parsed: pydantic writes UTC as `Z`.

    Args:
        value: An ISO-8601 time, or None.

    Returns:
        The time in the SDK's format, or None when no time was given.
    """
    if value is None:
        return None
    text = datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    return (
        text.removesuffix("+00:00") + "Z" if text.endswith("+00:00") else text
    )


def _connector_refused(reason: str) -> ZenMLBadRequest:
    return ZenMLBadRequest(f"connector configuration is not valid: {reason}")


def _configure(
    into: dict[str, Any],
    connector_type: Mapping[str, Any],
    auth_method: Any,
    resource_types: Any,
    resource_id: Any,
    configuration: Mapping[str, Any] | None,
    asking: list[Asked] | None = None,
    resent: list[str] | None = None,
) -> None:
    """Set what the SDK sets on a connector from its type's specification.

    This is ZenML's `_validate_and_configure_resources`: the resource types,
    with the resource id and instance support for one type, then the
    configuration its auth method's schema takes, without other keys. `into`
    is filled in the SDK's order, so a refusal leaves what was set before it.
    With `asking`, each secret attribute goes there for the page to ask, and
    one the call gives is refused. With `resent`, each secret value sent goes
    there.

    Args:
        into: The connector fields, filled in place.
        connector_type: The connector type's specification, as ZenML serves
            it.
        auth_method: The authentication method the connector uses.
        resource_types: The resource type, or a list of them; only a single
            one is configured with its resource id.
        resource_id: The resource id, kept for a single resource type.
        configuration: The configuration to check against the auth method's
            schema, or None to leave the configuration unset.
        asking: Where secret attributes go for the secret page to ask.
        resent: Where secret values sent again go.

    Raises:
        ZenMLBadRequest: When the type does not support the auth method or
            resource type, or the configuration is refused.
    """  # noqa: DOC503
    if isinstance(resource_types, list):
        resource_types = (
            resource_types[0] if len(resource_types) == 1 else None
        )
    name = connector_type.get("connector_type")
    methods = {
        m.get("auth_method"): m
        for m in connector_type.get("auth_methods") or []
    }
    kinds = {
        r.get("resource_type"): r
        for r in connector_type.get("resource_types") or []
    }
    if auth_method not in methods:
        raise _connector_refused(
            f"connector type {name!r} does not support the {auth_method!r} "
            f"authentication method. Supported authentication methods are: "
            f"{list(methods)}."
        )
    kind = None
    if resource_types is not None:
        if resource_types not in kinds:
            raise _connector_refused(
                f"connector type {name!r} does not support resource type "
                f"{resource_types!r}. Supported resource types are: {list(kinds)}."
            )
        kind = kinds[resource_types]
        if auth_method not in (kind.get("auth_methods") or []):
            raise _connector_refused(
                f"the {name!r} connector type does not support the {auth_method!r} "
                f"authentication method for the {resource_types!r} resource type."
            )
    if resource_types and kind:
        into |= {
            "resource_types": [kind["resource_type"]],
            "resource_id": resource_id,
            "supports_instances": kind.get("supports_instances", False),
        }
    else:
        # A connector for every resource type of its type, without a resource id.
        into |= {"resource_types": list(kinds), "supports_instances": False}
    if configuration is None:
        return
    schema = methods[auth_method].get("config_schema") or {}
    if asking is not None:
        refuse_keys(credentials_off_schema(configuration, schema))
    into["configuration"] = {}
    _configure_attributes(
        into["configuration"], schema, configuration, asking, resent
    )


def _configure_attributes(
    accepted: dict[str, Any],
    schema: Mapping[str, Any],
    configuration: Mapping[str, Any],
    asking: list[Asked] | None,
    resent: list[str] | None,
) -> None:
    """The configuration half of `_configure`, one attribute at a time.

    Attributes go in the schema's order, into `accepted` as it goes.

    Args:
        accepted: The accepted configuration, filled in place.
        schema: The auth method's configuration schema.
        configuration: The configuration given.
        asking: Where secret attributes go for the secret page to ask, or
            None to accept secret values.
        resent: Where secret values sent again go, or None.

    Raises:
        ZenMLUnsupported: When an attribute's schema can't be read.
        ZenMLBadRequest: When a secret is given while the page asks for it,
            a required attribute is missing, or a secret is not a string.
    """  # noqa: DOC503
    required = schema.get("required") or []
    for attribute, attribute_schema in (
        schema.get("properties") or {}
    ).items():
        if attribute_schema.get("anyOf"):
            options = [
                option
                for option in attribute_schema["anyOf"]
                if option.get("type", "string") != "null"
            ]
            if len(options) != 1:
                raise ZenMLUnsupported(
                    "Service connector schema error: this server can't read the "
                    "connector type's configuration schema, so it can't configure it."
                )
            attribute_schema = options[0]
        value = configuration.get(attribute)
        secret = attribute_schema.get("format", "") == "password"
        if secret and asking is not None:
            if value is not None:
                raise ZenMLBadRequest(
                    f"{attribute!r} is a secret: leave it out of `configuration`. "
                    "The user types it on the secret page this tool links to."
                )
            asking.append(
                Asked(
                    ("payload", "configuration", attribute),
                    attribute,
                    attribute in required,
                )
            )
            continue
        if value is None:
            if attribute in required:
                raise _connector_refused(
                    f"missing required attribute {attribute!r}"
                )
            continue
        if secret and not isinstance(value, str):
            raise _connector_refused(
                f"attribute {attribute!r} is a secret but is not a string"
            )
        if secret and resent is not None and value:
            resent.append(value)
        if (
            not secret
            and attribute_schema.get("type", "string") == "array"
            and isinstance(value, str)
        ):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = value.split(",")
        accepted[attribute] = value


def connector_as_the_sdk_holds(connector: Any) -> Any:
    """A connector ZenML answered with its configuration, as the SDK holds it.

    This is `RestZenStore`'s `_populate_connector_type`, then
    `validate_configuration`: its type marked as the server's and, when the answer carries the type's
    specification, its resource fields and configuration set again from it.
    The SDK only logs a refusal there, so what was set before it stays; an
    unreadable schema fails.

    Args:
        connector: The connector as ZenML answered it.

    Returns:
        The connector as the SDK holds it.
    """
    connector = with_remote_connector_type(connector)
    body, metadata = body_of(connector), meta_of(connector)
    connector_type = body.get("connector_type")
    if not isinstance(connector_type, dict):
        return connector
    fields: dict[str, Any] = {}
    with suppress(ZenMLBadRequest):
        _configure(
            fields,
            connector_type,
            body.get("auth_method"),
            body.get("resource_types"),
            body.get("resource_id"),
            metadata.get("configuration") or {},
        )
    configuration = fields.pop("configuration", None)
    connector = {**connector, "body": {**body, **fields}}
    if configuration is not None:
        connector["metadata"] = {**metadata, "configuration": configuration}
    return connector


async def create_service_connector(request: WriteRequest) -> dict[str, Any]:
    """The body the SDK's `create_service_connector` sends.

    With one resource type or auth method on the connector type, that one is
    used when the call names none.

    Args:
        request: The checked create.

    Returns:
        The request body, without null fields.

    Raises:
        ZenMLBadRequest: When no auth method is given and the type has
            several.
    """
    payload = request.payload
    connector_type = await request.read(
        "service_connector_type", payload["connector_type"]
    )
    kinds = connector_type.get("resource_types") or []
    resource_type = payload.get("resource_type")
    if not resource_type and len(kinds) == 1:
        resource_type = kinds[0].get("resource_type")
    auth_method = payload.get("auth_method")
    if not auth_method:
        methods = [
            m.get("auth_method")
            for m in connector_type.get("auth_methods") or []
        ]
        if len(methods) != 1:
            raise ZenMLBadRequest(
                "Multiple authentication methods are available for the "
                f"{connector_type.get('name')} service connector type. Please "
                f"specify one of the following: {methods}."
            )
        auth_method = methods[0]
    body: dict[str, Any] = {
        "name": payload["name"],
        "connector_type": payload["connector_type"],
        "description": payload.get("description", ""),
        "auth_method": auth_method,
        "expiration_seconds": payload.get("expiration_seconds"),
        "expires_at": _sdk_datetime(payload.get("expires_at")),
        "expires_skew_tolerance": payload.get("expires_skew_tolerance"),
        "labels": payload.get("labels") or {},
        # What the SDK's request model holds before the type configures it.
        "configuration": {},
    }
    _configure(
        body,
        connector_type,
        auth_method,
        resource_type,
        payload.get("resource_id"),
        payload.get("configuration"),
        request.asking,
    )
    # The SDK sends its model without the fields that are null.
    return {field: value for field, value in body.items() if value is not None}


def _given_or_existing(
    payload: Mapping[str, Any], entity: Any, field: str, cleared: Any
) -> Any:
    """The SDK's rule for a connector field.

    A value left out keeps the existing one, and `cleared` removes it.

    Args:
        payload: The update's payload.
        entity: The existing connector.
        field: The field's name.
        cleared: The value that removes the field.

    Returns:
        The value to send, or None to clear it.
    """
    given = payload.get(field)
    if given is None:
        return field_of(entity, field)
    return None if given == cleared else given


async def update_service_connector(
    request: WriteRequest, _: Any
) -> dict[str, Any]:
    """The body the SDK's `update_service_connector` sends.

    The existing entity passed in is not used: the SDK reads the connector
    itself, with its secrets when the update keeps the configuration.

    Args:
        request: The checked update.

    Returns:
        The request body.
    """
    payload = request.payload
    configuration = payload.get("configuration")
    # The SDK reads the connector itself, with its secrets when the update
    # keeps the existing configuration.
    connector = await request.client.get(
        f"{request.route}/{segment(str(request.target))}",
        params={"hydrate": True, "expand_secrets": configuration is None},
        what="Reading the service connector",
    )
    if configuration is None:
        connector = connector_as_the_sdk_holds(connector)
        configuration = meta_of(connector).get("configuration") or {}
    connector_type = field_of(connector, "connector_type")
    if not isinstance(connector_type, dict):
        connector_type = await request.read(
            "service_connector_type", str(connector_type)
        )
    resource_type = payload.get("resource_type")
    resource_types = (
        field_of(connector, "resource_types")
        if resource_type is None
        else resource_type or None
    )
    kinds = connector_type.get("resource_types") or []
    if not resource_type and len(kinds) == 1:
        resource_types = kinds[0].get("resource_type")
    labels = field_of(connector, "labels") or {}
    changes = payload.get("labels")
    if changes is not None:
        labels = {
            **{
                key: value
                for key, value in labels.items()
                if key not in changes
            },
            **{
                key: value
                for key, value in changes.items()
                if value is not None
            },
        }
    auth_method = payload.get("auth_method") or field_of(
        connector, "auth_method"
    )
    body: dict[str, Any] = {
        "name": payload.get("name") or connector.get("name"),
        "connector_type": connector_type.get("connector_type"),
        "description": payload.get("description")
        or field_of(connector, "description"),
        "auth_method": auth_method,
        "expires_at": _sdk_datetime(payload.get("expires_at")),
        "expires_skew_tolerance": payload.get("expires_skew_tolerance"),
        "expiration_seconds": _given_or_existing(
            payload, connector, "expiration_seconds", 0
        ),
    }
    _configure(
        body,
        connector_type,
        auth_method,
        resource_types,
        _given_or_existing(payload, connector, "resource_id", ""),
        configuration,
        # Only the call's own configuration asks: a kept one is resent.
        request.asking if payload.get("configuration") is not None else None,
        request.resent if payload.get("configuration") is None else None,
    )
    return {**body, "labels": labels}
