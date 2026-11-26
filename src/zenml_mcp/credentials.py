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
"""How tools keep credentials out of their arguments and answers.

This covers which key names count as one, how answers mask them, the
refusals, which secret writes take their secret on the secret page instead
(which runs them and shows their answer), and which flavor configuration
fields are secret.

Each secret write names the field its secret travels in (its type's
`secret_fields` in `resource_catalog.py`).
When the secret page runs the write, that field skips the key-name refusal as
upstream; a tool call links to the page instead, which asks for it (`Asked`),
and the call may not carry it.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from zenml_mcp.call import Asked, ZenMLCall
from zenml_mcp.client import UNREADABLE, ZenMLBadRequest
from zenml_mcp.common import meta_of
from zenml_mcp.registry import PageOutcome, SecretWrites
from zenml_mcp.resource_catalog import RESOURCE_REGISTRY

# Whole key segments (split on `_`, `-`, `.` and camelCase), so `api_token` and
# `access_key_id` are masked but ML parameters like `max_tokens` or
# `tokenizer_name` are not.
_SENSITIVE_SEGMENTS = frozenset(
    {
        "password",
        "passwd",
        "pwd",
        "secret",
        "token",
        "credential",
        "credentials",
        "apikey",
    }
)
# Nouns that name a credential only as a key's last segment: `Authorization`
# and `Proxy-Authorization` carry one, `authorization_mode` does not.
_SENSITIVE_LAST = frozenset({"authorization"})
_SENSITIVE_PAIRS = frozenset(
    {
        ("api", "key"),
        ("access", "key"),
        ("private", "key"),
        ("secret", "key"),
        ("auth", "key"),
    }
)


def is_sensitive_key(key: Any) -> bool:
    """Whether a key's name looks like a credential.

    The key is split into whole segments, so `api_token` counts and
    `max_tokens` does not.

    Args:
        key: The key; anything but a string is read as its `str()`.

    Returns:
        Whether a segment, a pair of adjacent segments, or the last segment
        names a credential.
    """
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(key))
    segments = [
        part for part in re.split(r"[^a-z0-9]+", spaced.lower()) if part
    ]
    return (
        any(part in _SENSITIVE_SEGMENTS for part in segments)
        or any(
            pair in _SENSITIVE_PAIRS for pair in zip(segments, segments[1:])
        )
        or bool(segments and segments[-1] in _SENSITIVE_LAST)
    )


def redact(value: Any) -> Any:
    """Mask values under credential-like keys in parameters and metadata.

    Run parameters and metadata are needed for debugging, but a key named like
    a credential never goes back to the model.

    Args:
        value: The value to mask, searched through nested dicts and lists.

    Returns:
        A copy with `***` under every credential-like key.
    """
    if isinstance(value, dict):
        return {
            k: "***" if is_sensitive_key(k) else redact(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def credential_like_keys(value: Any, prefix: str = "") -> list[str]:
    """Paths of the keys in a tool argument that look like credentials.

    A credential-like key is reported without looking inside its value.

    Args:
        value: The argument, searched through nested dicts and lists.
        prefix: The path of `value` itself, prepended to each key found.

    Returns:
        Dotted paths of the credential-like keys; list items appear by index.
    """
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}{key}"
            if is_sensitive_key(key):
                found.append(path)
            else:
                found.extend(credential_like_keys(item, f"{path}."))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(credential_like_keys(item, f"{prefix}{index}."))
    return found


def refuse_run_credentials(
    values: dict[str, Any] | None,
    argument: str = "run_configuration",
    advice: str = "name the secret in `secrets`",
) -> None:
    """Refuse run settings that carry a credential-like key.

    Args:
        values: The run settings, if any.
        argument: The argument's name, for the refusal.
        advice: Where the refusal points the caller instead.

    Raises:
        ZenMLBadRequest: When a key looks like a credential.
    """
    credentials = credential_like_keys(values)
    if credentials:
        named = ", ".join(repr(key) for key in credentials)
        raise ZenMLBadRequest(
            f"{argument} keys that look like credentials: {named}. "
            "Credentials never go through this tool. Store them as a ZenML "
            f"secret and {advice}."
        )


def component_credentials_refused(keys: list[str]) -> ZenMLBadRequest:
    """The refusal for credential-like configuration keys.

    It names the keys, never their values.

    Args:
        keys: The credential-like keys.

    Returns:
        The error to raise, which points to a service connector instead.
    """
    named = ", ".join(repr(k) for k in keys)
    plural = len(keys) > 1
    return ZenMLBadRequest(
        f"Configuration key{'s' if plural else ''} {named} "
        f"look{'' if plural else 's'} like a credential. Credentials never go "
        "through this tool: the user registers a service connector in their own "
        "terminal (for example `zenml service-connector register my-aws --type "
        "aws --auto-configure`) and you pass its ID as connector_id. Only "
        "non-secret settings such as paths, URIs, regions or namespaces belong "
        "in configuration."
    )


_ISSUED = "Leave it empty and ZenML issues one, shown here once."
WEBHOOK_SECRET = Asked(
    ("payload", "secret"), f"Signing secret. {_ISSUED}", required=False
)
NEW_WEBHOOK_SECRET = Asked(
    ("payload", "secret"), f"New signing secret. {_ISSUED}", required=False
)


def refuse_keys(keys: list[str]) -> None:
    """Refuse a payload whose keys look like credentials.

    Args:
        keys: The credential-like key paths found in the payload.

    Raises:
        ZenMLBadRequest: When there is any.
    """
    if keys:
        named = ", ".join(repr(key) for key in keys)
        raise ZenMLBadRequest(
            f"payload keys that look like credentials: {named}. Credentials "
            "never go through this tool. Store them as a ZenML secret or in a "
            "service connector, from the user's own terminal."
        )


def _refuse_credentials(payload: Any) -> None:
    refuse_keys(credential_like_keys(payload))


# With a secret page, the secret writes a tool offers only through it: the
# page asks the user for the secret, and the tool answers with its link and
# writes nothing. A connector write whose call needs no secret is written
# directly.
THROUGH_THE_PAGE = frozenset(
    (resource_type, name)
    for resource_type, spec in RESOURCE_REGISTRY.items()
    for name in spec.secret_fields
)


def through_the_page(call: ZenMLCall) -> frozenset[tuple[str, str]]:
    """The secret writes that go through the call's secret page.

    Args:
        call: The tool call.

    Returns:
        Every secret write with a page, and none without, so that a secret
        in the arguments is written.
    """
    return THROUGH_THE_PAGE if call.secret_page is not None else frozenset()


def awaiting_user(
    call: ZenMLCall,
    tool: str,
    arguments: dict[str, Any],
    asked: Sequence[Asked],
) -> dict[str, Any]:
    """The call's secret page's answer in place of a secret write.

    Args:
        call: The tool call, which has a secret page.
        tool: The tool's name.
        arguments: The call's arguments, without the secret.
        asked: The secrets the page asks for.

    Returns:
        The page's answer.

    Raises:
        RuntimeError: When the call has no secret page.
    """
    if call.secret_page is None:
        raise RuntimeError("This call has no page to type a secret on.")
    return call.secret_page.awaiting_user(tool, arguments, asked)


def secret_writes(
    operation: str, paths: Mapping[tuple[str, str], tuple[str, ...]]
) -> SecretWrites:
    """The secret writes of a generic write tool.

    Args:
        operation: The tool's operation; an action names its own.
        paths: For each secret write, where its secret may go.

    Returns:
        What a secret page needs to run them.
    """

    def names(arguments: Mapping[str, Any]) -> tuple[str, str]:
        name = arguments.get("action") or operation
        return str(arguments.get("resource_type")), str(name)

    return SecretWrites(names, paths, _page_outcome)


def _page_outcome(content: Mapping[str, Any]) -> PageOutcome:
    """A generic write's answer on the secret page.

    A lost answer leaves the outcome unknown, and so does one ZenML took but
    sent back unreadable.

    Args:
        content: The write tool's answer.

    Returns:
        What the page shows of it.
    """
    error = content.get("error") or {}
    item = content.get("item") or {}
    return PageOutcome(
        unknown=content.get("outcome") == "unknown"
        or error.get("message") == UNREADABLE,
        check=(content.get("reconciliation") or {}).get("note") or "",
        name=item.get("name"),
        identifier=content.get("resource_id") or item.get("id"),
        issued=content.get("issued_secret"),
    )


def refuse_credentials_but_secrets(
    resource_type: str,
    name: str,
    payload: Any,
    through: frozenset[tuple[str, str]],
) -> None:
    """The key-name refusal, without the secret field of a secret write.

    The field skips the refusal when the secret page runs the write. A tool
    call links to the page, where the secret is the page's to ask for, so the
    field stays refused there.

    Args:
        resource_type: The catalogued type written.
        name: The operation or action.
        payload: The write's payload.
        through: The secret writes that go through the secret page.

    Raises:
        ZenMLBadRequest: When a tool call carries credential-like keys in the
            secret field the page asks for.
    """
    write = (resource_type, name)
    spec = RESOURCE_REGISTRY.get(resource_type)
    field = spec.secret_fields.get(name) if spec else None
    direct = write not in through
    if field and direct and isinstance(payload, dict):
        payload = {
            key: value for key, value in payload.items() if key != field
        }
    elif (
        field
        and write in through
        and isinstance(payload, dict)
        and field in payload
    ):
        if field == "configuration":
            # The connector type's schema decides which keys are secret, once
            # the write reads it (`credentials_off_schema`).
            payload = {
                key: value for key, value in payload.items() if key != field
            }
        elif keys := credential_like_keys({field: payload[field]}):
            named = ", ".join(repr(key) for key in keys)
            raise ZenMLBadRequest(
                f"payload keys that look like credentials: {named}. Leave them "
                "out: the user types them on the secret page this tool links to."
            )
    _refuse_credentials(payload)


def credentials_off_schema(
    configuration: Mapping[str, Any], schema: Mapping[str, Any]
) -> list[str]:
    """With a secret page, the key-name refusal for a connector's configuration.

    The configuration's values are strings. An attribute the auth method's
    schema names is the schema's to call secret, whatever its name, so only
    the other keys are checked.

    Args:
        configuration: The connector's configuration.
        schema: The auth method's JSON schema.

    Returns:
        Paths of the credential-like keys the schema doesn't name.
    """
    properties = schema.get("properties") or {}
    unnamed = {k: v for k, v in configuration.items() if k not in properties}
    return credential_like_keys(unnamed, "configuration.")


_FIELD_DESCRIPTION_MAX = 240


def _attribute_docs(description: str) -> dict[str, str]:
    """`name: text` entries from the "Attributes:" section of a config docstring.

    Args:
        description: The config class's docstring, as its schema holds it.

    Returns:
        Each attribute's text by name, continuation lines joined.
    """
    docs: dict[str, str] = {}
    lines = description.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.strip() == "Attributes:"),
        None,
    )
    if start is None:
        return docs
    current: str | None = None
    for line in lines[start + 1 :]:
        if not line.strip():
            current = None
            continue
        match = re.match(r"^\s{2,}([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if match:
            current = match.group(1)
            docs[current] = match.group(2).strip()
        elif current and line.startswith(" "):
            docs[current] = f"{docs[current]} {line.strip()}".strip()
        else:
            break
    return docs


def _schema_type(spec: dict[str, Any]) -> str | None:
    if isinstance(spec.get("type"), str):
        return spec["type"]
    for option in spec.get("anyOf") or []:
        if isinstance(option, dict) and option.get("type") not in (
            None,
            "null",
        ):
            return option.get("type")
    return None


def _clip_words(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def config_fields(schema: Any) -> list[dict[str, Any]]:
    """A flavor's configuration fields from its JSON schema, required first.

    `sensitive` marks credential fields (ZenML's SecretField, or a name that
    looks like one): those come from a service connector or a ZenML secret,
    never through `zenml_create_stack_component`.

    Args:
        schema: The flavor's config schema; anything but a dict has no fields.

    Returns:
        One entry per field. A sensitive field's default is left out.
    """
    if not isinstance(schema, dict):
        return []
    required = set(schema.get("required") or [])
    docs = _attribute_docs(schema.get("description") or "")
    fields = []
    for name, spec in (schema.get("properties") or {}).items():
        if not isinstance(spec, dict):
            continue
        sensitive = bool(spec.get("sensitive")) or is_sensitive_key(name)
        default = spec.get("default")
        description = spec.get("description") or docs.get(name)
        fields.append(
            {
                "name": name,
                "title": spec.get("title"),
                "type": _schema_type(spec),
                "required": name in required,
                "sensitive": sensitive,
                "default": default
                if not sensitive
                and isinstance(default, str | int | float | bool)
                else None,
                "description": _clip_words(description, _FIELD_DESCRIPTION_MAX)
                if description
                else None,
            }
        )
    fields.sort(key=lambda f: not f["required"])
    return fields


def flavor_secret_keys(
    flavor: Any, configuration: Mapping[str, Any]
) -> list[str]:
    """The configuration keys that a flavor's schema marks as credentials.

    Args:
        flavor: The flavor as ZenML returns it, with its config schema.
        configuration: The configuration to check.

    Returns:
        The given keys that are sensitive fields of the flavor.
    """
    fields = config_fields(meta_of(flavor).get("config_schema"))
    return [
        f["name"]
        for f in fields
        if f["sensitive"] and f["name"] in configuration
    ]
