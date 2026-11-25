#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
"""Shared contracts for stateless webhook providers."""

import hashlib
import hmac
import json
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from zenml.enums import GenericFilterOps
from zenml.exceptions import CredentialsNotValid
from zenml.models.v2.base.filter import StringFilterOption
from zenml.utils.enum_utils import StrEnum
from zenml.utils.pydantic_utils import YAMLSerializationMixin

if TYPE_CHECKING:
    from zenml.models import WebhookTriggerResponse
    from zenml.webhooks.events import WebhookEvent


WebhookTriggerT = TypeVar("WebhookTriggerT")

_WEBHOOK_STRING_FILTER_OPERATORS = {
    GenericFilterOps.EQUALS,
    GenericFilterOps.NOT_EQUALS,
    GenericFilterOps.CONTAINS,
    GenericFilterOps.NOT_CONTAINS,
    GenericFilterOps.STARTSWITH,
    GenericFilterOps.ENDSWITH,
    GenericFilterOps.ONEOF,
    GenericFilterOps.NOT_ONEOF,
}
_WEBHOOK_NEGATIVE_STRING_FILTER_OPERATORS = {
    GenericFilterOps.NOT_EQUALS,
    GenericFilterOps.NOT_CONTAINS,
    GenericFilterOps.NOT_ONEOF,
}

WEBHOOK_FILTER_MAX_EXPRESSIONS = 10
WEBHOOK_FILTER_MAX_EXPRESSION_LENGTH = 512
WEBHOOK_FILTER_MAX_ONEOF_CHOICES = 10
WEBHOOK_MAX_TARGET_EVENTS = 10


class WebhookAuthenticationError(CredentialsNotValid):
    """Raised when a webhook request cannot be authenticated."""


class WebhookPayloadError(ValueError):
    """Raised when a webhook payload fails fundamental validation."""


class WebhookPreValidationResult(StrEnum):
    """Possible outcomes of provider header pre-validation."""

    PROCESS = "process"
    IGNORE = "ignore"


class WebhookTargetEvent(BaseModel):
    """Shared shape of a provider-specific target event."""

    model_config = ConfigDict(extra="forbid")

    type: str

    @staticmethod
    def _validate_filter(
        value: StringFilterOption,
        *,
        field_name: str,
    ) -> StringFilterOption:
        """Validate one webhook event string filter.

        Args:
            value: The filter value to validate.
            field_name: The name of the filtered event field.

        Returns:
            The validated filter value.

        Raises:
            ValueError: If the filter value or operator is invalid.
        """
        if value is None:
            return None
        items = value if isinstance(value, list) else [value]
        if not items:
            raise ValueError(f"Webhook event filter '{field_name}' is empty.")
        if len(items) > WEBHOOK_FILTER_MAX_EXPRESSIONS:
            raise ValueError(
                f"Webhook event filter '{field_name}' supports at most "
                f"{WEBHOOK_FILTER_MAX_EXPRESSIONS} expressions."
            )
        for item in items:
            if not item:
                raise ValueError(
                    f"Webhook event filter '{field_name}' is empty."
                )
            if len(item) > WEBHOOK_FILTER_MAX_EXPRESSION_LENGTH:
                raise ValueError(
                    f"Webhook event filter '{field_name}' expressions must "
                    f"not exceed {WEBHOOK_FILTER_MAX_EXPRESSION_LENGTH} "
                    "characters."
                )
            if ":" not in item:
                continue
            operator, operand = item.split(":", 1)
            if operator not in _WEBHOOK_STRING_FILTER_OPERATORS:
                continue
            if not operand:
                raise ValueError(
                    f"Webhook event filter '{field_name}' has an empty "
                    "operand."
                )
            if operator in {
                GenericFilterOps.ONEOF,
                GenericFilterOps.NOT_ONEOF,
            }:
                try:
                    choices = json.loads(operand)
                except json.JSONDecodeError as error:
                    raise ValueError(
                        f"Webhook event filter '{field_name}' requires a "
                        f"JSON-formatted list for '{operator}'."
                    ) from error
                if (
                    not isinstance(choices, list)
                    or not choices
                    or len(choices) > WEBHOOK_FILTER_MAX_ONEOF_CHOICES
                    or not all(
                        isinstance(choice, str) and choice
                        for choice in choices
                    )
                ):
                    raise ValueError(
                        f"Webhook event filter '{field_name}' requires a "
                        "non-empty JSON list of at most "
                        f"{WEBHOOK_FILTER_MAX_ONEOF_CHOICES} strings for "
                        f"'{operator}'."
                    )
        return value

    @model_validator(mode="after")
    def validate_filters(self) -> "WebhookTargetEvent":
        """Validate all configured string filters.

        Returns:
            The validated target event.
        """
        for field_name, field in type(self).model_fields.items():
            if cast(Any, field.annotation) != StringFilterOption:
                continue
            self._validate_filter(
                getattr(self, field_name),
                field_name=field_name,
            )
        return self


def _matches_string_filter_value(*, actual: str, configured: str) -> bool:
    """Match one actual string against one configured filter expression.

    Args:
        actual: The value extracted from the webhook event.
        configured: One validated string filter expression.

    Returns:
        Whether the actual value satisfies the expression.
    """
    if ":" not in configured:
        return actual == configured
    operator, operand = configured.split(":", 1)
    if operator not in _WEBHOOK_STRING_FILTER_OPERATORS:
        return actual == configured
    if operator == GenericFilterOps.EQUALS:
        return actual == operand
    if operator == GenericFilterOps.NOT_EQUALS:
        return actual != operand
    if operator == GenericFilterOps.CONTAINS:
        return operand in actual
    if operator == GenericFilterOps.NOT_CONTAINS:
        return operand not in actual
    if operator == GenericFilterOps.STARTSWITH:
        return actual.startswith(operand)
    if operator == GenericFilterOps.ENDSWITH:
        return actual.endswith(operand)
    if operator == GenericFilterOps.ONEOF:
        return actual in json.loads(operand)
    if operator == GenericFilterOps.NOT_ONEOF:
        return actual not in json.loads(operand)
    return False


def _is_negative_string_filter(configured: str) -> bool:
    """Return whether a string filter expression uses a negative operator.

    Args:
        configured: One validated string filter expression.

    Returns:
        Whether the expression negates a match.
    """
    operator, separator, _ = configured.partition(":")
    return bool(
        separator and operator in _WEBHOOK_NEGATIVE_STRING_FILTER_OPERATORS
    )


def matches_string_filter(
    *, actual: str | None, configured: StringFilterOption
) -> bool:
    """Match an extracted value against a supported string filter.

    Args:
        actual: The value extracted from the webhook event.
        configured: The configured string filter or OR-list of filters.

    Returns:
        Whether the extracted value matches the configured filter.
    """
    if configured is None:
        return True
    if actual is None:
        return False
    configured_values = (
        configured if isinstance(configured, list) else [configured]
    )
    return any(
        _matches_string_filter_value(actual=actual, configured=value)
        for value in configured_values
    )


def matches_string_collection_filter(
    *, actual: Sequence[str], configured: StringFilterOption
) -> bool:
    """Match a collection against a configured string filter.

    Args:
        actual: Values extracted from the webhook event.
        configured: The configured string filter or OR-list of filters.

    Returns:
        Whether any value satisfies a positive filter or every value satisfies
        a negative filter.
    """
    if configured is None:
        return True
    if not actual:
        return False
    for configured_value in (
        configured if isinstance(configured, list) else [configured]
    ):
        aggregate = (
            all if _is_negative_string_filter(configured_value) else any
        )
        if aggregate(
            _matches_string_filter_value(
                actual=actual_value, configured=configured_value
            )
            for actual_value in actual
        ):
            return True
    return False


class WebhookConfiguration(YAMLSerializationMixin):
    """Base class for provider-owned webhook configuration."""


class ParsedWebhookEvent(BaseModel):
    """Provider delivery parsed into provider-neutral metadata."""

    event_type: str
    delivery_id: str | None = None
    payload: dict[str, Any]


class WebhookTriggerMatch(BaseModel, Generic[WebhookTriggerT]):
    """Result of matching one trusted event to webhook triggers."""

    model_config = ConfigDict(frozen=True)

    triggers: list[WebhookTriggerT]
    event: dict[str, Any] | None = None


class WebhookIntakeResponse(BaseModel):
    """Provider-owned successful webhook intake response."""

    status_code: int = Field(default=202, ge=200, lt=300)
    body: str | None = None
    media_type: str | None = None


class ParsedWebhookDelivery(BaseModel):
    """A successful provider delivery and its intake response."""

    event: ParsedWebhookEvent | None
    response: WebhookIntakeResponse = Field(
        default_factory=WebhookIntakeResponse
    )


class BaseWebhookProvider(ABC):
    """Stateless provider behavior used by intake and trigger matching."""

    webhook_type: ClassVar[str]
    configuration_class: ClassVar[type[WebhookConfiguration]]

    async def pre_validate(
        self, headers: Mapping[str, str]
    ) -> WebhookPreValidationResult:
        """Validate headers before webhook lookup and body reading.

        Args:
            headers: The untrusted request headers.

        Returns:
            Whether generic intake should process or ignore the delivery.

        """
        return WebhookPreValidationResult.PROCESS

    @abstractmethod
    def authenticate(
        self, body: bytes, headers: Mapping[str, str], secret: str
    ) -> None:
        """Authenticate the exact raw request body.

        Args:
            body: The raw request body.
            headers: The request headers.
            secret: The webhook signing secret.

        Raises:
            WebhookAuthenticationError: If authentication fails.
        """

    def parse(
        self, body: bytes, headers: Mapping[str, str]
    ) -> ParsedWebhookEvent:
        """Parse a delivery into provider-neutral event data.

        Args:
            body: The raw request body.
            headers: The request headers.

        Returns:
            The parsed delivery.

        Raises:
            WebhookPayloadError: If the body or metadata is invalid.
        """
        try:
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise WebhookPayloadError(
                "Request body must be valid JSON."
            ) from error
        if not isinstance(payload, dict):
            raise WebhookPayloadError(
                "Request body must contain a top-level JSON object."
            )
        return ParsedWebhookEvent(
            event_type=self.get_event_type(payload=payload, headers=headers),
            delivery_id=self.get_delivery_id(payload=payload, headers=headers),
            payload=payload,
        )

    def parse_delivery(
        self, body: bytes, headers: Mapping[str, str]
    ) -> ParsedWebhookDelivery:
        """Parse a successful delivery and select its intake response.

        Existing providers can continue to implement :meth:`parse`; providers
        with control deliveries or custom responses can override this method.

        Args:
            body: The raw request body.
            headers: The request headers.

        Returns:
            The parsed delivery and provider-owned response.
        """
        return ParsedWebhookDelivery(event=self.parse(body, headers))

    @abstractmethod
    def get_event_type(
        self, payload: dict[str, Any], headers: Mapping[str, str]
    ) -> str:
        """Extract the provider event type.

        Args:
            payload: The parsed JSON payload.
            headers: The request headers.

        Returns:
            The provider event type.

        Raises:
            WebhookPayloadError: If the type is missing or invalid.
        """

    def get_delivery_id(
        self, payload: dict[str, Any], headers: Mapping[str, str]
    ) -> str | None:
        """Extract the optional delivery ID.

        Args:
            payload: The parsed JSON payload.
            headers: The request headers.

        Returns:
            The delivery ID, if present.
        """
        return None

    def validate_configuration(
        self,
        configuration: WebhookConfiguration | Mapping[str, Any],
    ) -> WebhookConfiguration:
        """Strictly validate a configuration for persistence.

        Args:
            configuration: The provider-neutral configuration.

        Returns:
            A normalized provider-neutral configuration.

        Raises:
            TypeError: If a configuration for another provider is supplied.
        """
        if isinstance(configuration, Mapping):
            return self.configuration_class.model_validate(configuration)
        if isinstance(configuration, self.configuration_class):
            return configuration
        raise TypeError(
            "Expected a mapping or an instance of "
            f"{self.configuration_class.__name__}, got "
            f"{type(configuration).__name__}."
        )

    @abstractmethod
    def match_triggers(
        self,
        *,
        event: "WebhookEvent",
        candidates: Sequence["WebhookTriggerResponse"],
    ) -> "WebhookTriggerMatch[WebhookTriggerResponse]":
        """Match candidates and return the parsed semantic event.

        Args:
            event: The trusted webhook event.
            candidates: Triggers selected by generic orchestration.

        Returns:
            The matching triggers and any parsed semantic event.
        """


def authenticate_hmac_sha256(
    *,
    body: bytes,
    headers: Mapping[str, str],
    secret: str,
    header: str,
    prefixed: bool = True,
) -> None:
    """Authenticate an HMAC-SHA256 signature.

    Args:
        body: The exact request body.
        headers: The request headers.
        secret: The signing secret.
        header: The signature header name.
        prefixed: If `True`, require a `sha256=` prefix (GitHub-style). If
            `False`, compare the raw hexadecimal digest (ClickUp-style).

    Raises:
        WebhookAuthenticationError: If the signature is invalid.
    """
    signature = headers.get(header)
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if prefixed:
        if not signature or not signature.startswith("sha256="):
            raise WebhookAuthenticationError(
                f"Missing or malformed {header} header."
            )
        expected = "sha256=" + digest
        if not hmac.compare_digest(signature, expected):
            raise WebhookAuthenticationError("Invalid webhook signature.")
        return
    if not signature:
        raise WebhookAuthenticationError(f"Missing {header} header.")
    if not hmac.compare_digest(signature.lower(), digest.lower()):
        raise WebhookAuthenticationError("Invalid webhook signature.")
