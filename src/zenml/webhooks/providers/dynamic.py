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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Dynamic webhook target filters over authenticated JSON payloads."""

import json
import re
from collections.abc import Callable, Mapping
from typing import Any, Literal

from pydantic import Field, PrivateAttr, model_validator

from zenml.webhooks.providers.base import (
    WebhookTargetEvent,
    matches_string_collection_filter,
    matches_string_filter,
)

WEBHOOK_DYNAMIC_FILTER_MAX_PATHS = 10
WEBHOOK_DYNAMIC_FILTER_MAX_PATH_LENGTH = 512
WEBHOOK_DYNAMIC_FILTER_MAX_SEGMENTS = 8
WEBHOOK_DYNAMIC_FILTER_MAX_WILDCARDS = 1

_BARE_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")


class _Wildcard:
    """Marker for a wildcard array projection."""


_WILDCARD = _Wildcard()
_PathToken = str | int | _Wildcard


def _invalid_path_message(path: str, reason: str) -> str:
    """Create a consistent dynamic path validation error message.

    Args:
        path: The configured payload path.
        reason: The validation failure.

    Returns:
        The path validation error message.
    """
    return f"Invalid dynamic webhook filter path '{path}': {reason}"


def _parse_bracket(path: str, position: int) -> tuple[_PathToken, int]:
    """Parse one bracket path segment.

    Args:
        path: The complete payload path.
        position: The position of the opening bracket.

    Returns:
        The parsed token and the next unread position.

    Raises:
        ValueError: If the bracket segment is malformed.
    """
    value_position = position + 1
    if value_position >= len(path):
        raise ValueError(_invalid_path_message(path, "unclosed bracket"))

    if path[value_position] == '"':
        try:
            key, end = json.JSONDecoder().raw_decode(path, value_position)
        except json.JSONDecodeError as error:
            raise ValueError(
                _invalid_path_message(path, "invalid quoted object key")
            ) from error
        if not isinstance(key, str) or end >= len(path) or path[end] != "]":
            raise ValueError(
                _invalid_path_message(
                    path, "quoted object keys must end with ']'"
                )
            )
        return key, end + 1

    end = path.find("]", value_position)
    if end < 0:
        raise ValueError(_invalid_path_message(path, "unclosed bracket"))
    value = path[value_position:end]
    if value == "*":
        return _WILDCARD, end + 1
    if value.isdigit():
        return int(value), end + 1
    raise ValueError(
        _invalid_path_message(
            path,
            "brackets require a non-negative index, '*', or JSON-quoted key",
        )
    )


def _parse_dynamic_path(path: str) -> tuple[_PathToken, ...]:
    """Parse and validate a constrained dynamic webhook payload path.

    Args:
        path: The configured payload path.

    Returns:
        The compiled path tokens.

    Raises:
        ValueError: If the path does not follow the supported grammar.
    """
    if not path:
        raise ValueError(_invalid_path_message(path, "path must not be empty"))
    if len(path) > WEBHOOK_DYNAMIC_FILTER_MAX_PATH_LENGTH:
        raise ValueError(
            _invalid_path_message(
                path,
                "path must not exceed "
                f"{WEBHOOK_DYNAMIC_FILTER_MAX_PATH_LENGTH} characters",
            )
        )

    tokens: list[_PathToken] = []
    position = 0
    if path.startswith('["'):
        token, position = _parse_bracket(path, position)
        tokens.append(token)
    else:
        match = _BARE_KEY.match(path, position)
        if match is None:
            raise ValueError(
                _invalid_path_message(
                    path, "path must start with an object key"
                )
            )
        tokens.append(match.group())
        position = match.end()

    while position < len(path):
        character = path[position]
        if character == ".":
            position += 1
            match = _BARE_KEY.match(path, position)
            if match is None:
                raise ValueError(
                    _invalid_path_message(
                        path, "'.' must be followed by an object key"
                    )
                )
            tokens.append(match.group())
            position = match.end()
        elif character == "[":
            token, position = _parse_bracket(path, position)
            tokens.append(token)
        else:
            raise ValueError(
                _invalid_path_message(
                    path, f"unexpected character at position {position}"
                )
            )

        if len(tokens) > WEBHOOK_DYNAMIC_FILTER_MAX_SEGMENTS:
            raise ValueError(
                _invalid_path_message(
                    path,
                    "path must not contain more than "
                    f"{WEBHOOK_DYNAMIC_FILTER_MAX_SEGMENTS} segments",
                )
            )

    wildcard_count = sum(token is _WILDCARD for token in tokens)
    if wildcard_count > WEBHOOK_DYNAMIC_FILTER_MAX_WILDCARDS:
        raise ValueError(
            _invalid_path_message(
                path,
                "path must not contain more than "
                f"{WEBHOOK_DYNAMIC_FILTER_MAX_WILDCARDS} wildcard",
            )
        )
    return tuple(tokens)


def _resolve_dynamic_path(
    payload: Mapping[str, Any], tokens: tuple[_PathToken, ...]
) -> list[Any]:
    """Resolve compiled path tokens without treating failures as errors.

    Args:
        payload: The authenticated JSON payload.
        tokens: The compiled path tokens.

    Returns:
        Every value resolved by the path.
    """
    values: list[Any] = [payload]
    for token in tokens:
        resolved: list[Any] = []
        for value in values:
            if token is _WILDCARD:
                if isinstance(value, list):
                    resolved.extend(value)
            elif isinstance(token, int):
                if isinstance(value, list) and token < len(value):
                    resolved.append(value[token])
            elif isinstance(value, Mapping) and token in value:
                resolved.append(value[token])
        values = resolved
        if not values:
            break
    return values


def _stringify_json_scalar(value: Any) -> str | None:
    """Convert a JSON scalar to its stable matching representation.

    Args:
        value: A resolved JSON value.

    Returns:
        The string representation, or `None` for objects and arrays.
    """
    if isinstance(value, str):
        return value
    if value is None or isinstance(value, (bool, int, float)):
        try:
            return json.dumps(value, allow_nan=False, separators=(",", ":"))
        except ValueError:
            return None
    return None


class DynamicWebhookTargetEvent(WebhookTargetEvent):
    """User-defined webhook event filter over an authenticated JSON body."""

    type: Literal["dynamic"] = "dynamic"
    event_type: str | list[str]
    filters: dict[str, str | list[str]] = Field(
        default_factory=dict,
        max_length=WEBHOOK_DYNAMIC_FILTER_MAX_PATHS,
    )

    _compiled_filters: dict[str, tuple[_PathToken, ...]] = PrivateAttr(
        default_factory=dict
    )

    @model_validator(mode="after")
    def validate_dynamic_filters(self) -> "DynamicWebhookTargetEvent":
        """Validate body filters and compile their paths.

        Returns:
            The validated dynamic target event.
        """
        self._validate_filter(self.event_type, field_name="event_type")

        compiled_filters: dict[str, tuple[_PathToken, ...]] = {}
        for path, configured in self.filters.items():
            self._validate_filter(configured, field_name=path)
            compiled_filters[path] = _parse_dynamic_path(path)
        self._compiled_filters = compiled_filters
        return self

    def matches(self, *, event_type: str, payload: Mapping[str, Any]) -> bool:
        """Match a provider event type and authenticated JSON body.

        Args:
            event_type: The provider-specific raw event type.
            payload: The complete authenticated JSON body.

        Returns:
            Whether the event satisfies every configured filter.
        """
        if not matches_string_filter(
            actual=event_type, configured=self.event_type
        ):
            return False
        for path, configured in self.filters.items():
            actual_values = [
                string_value
                for value in _resolve_dynamic_path(
                    payload, self._compiled_filters[path]
                )
                if (string_value := _stringify_json_scalar(value)) is not None
            ]
            if not matches_string_collection_filter(
                actual=actual_values, configured=configured
            ):
                return False
        return True


def matches_webhook_target(
    *,
    target: WebhookTargetEvent,
    event_type: str,
    payload: Mapping[str, Any],
    semantic_matcher: Callable[[Any], bool] | None,
) -> bool:
    """Dispatch matching to a dynamic or provider-semantic target.

    Args:
        target: The configured webhook target.
        event_type: The provider-specific raw event type.
        payload: The complete authenticated JSON body.
        semantic_matcher: Provider semantic matching, when parsing succeeded.

    Returns:
        Whether the provider event matches the target.
    """
    if isinstance(target, DynamicWebhookTargetEvent):
        return target.matches(event_type=event_type, payload=payload)
    return semantic_matcher is not None and semantic_matcher(target)
