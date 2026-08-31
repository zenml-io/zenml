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
from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel, ConfigDict, model_validator

from zenml.exceptions import CredentialsNotValid
from zenml.models.v2.base.filter import StringFilterOption
from zenml.utils.enum_utils import StrEnum
from zenml.utils.pydantic_utils import YAMLSerializationMixin

if TYPE_CHECKING:
    from zenml.models import WebhookTriggerResponse
    from zenml.webhooks.events import WebhookEvent


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

    @classmethod
    @abstractmethod
    def get_prefix_matching_support(cls) -> Mapping[str, bool]:
        """Get prefix matching support for string filter fields.

        Returns:
            Filter fields mapped to whether they allow `startswith`.
        """

    @staticmethod
    def _validate_filter(
        value: StringFilterOption,
        *,
        field_name: str,
        allow_startswith: bool,
    ) -> StringFilterOption:
        """Validate one webhook event string filter."""
        if value is None:
            return None
        allowed = {"oneof"}
        if allow_startswith:
            allowed.add("startswith")
        for item in value if isinstance(value, list) else [value]:
            if not item:
                raise ValueError(
                    f"Webhook event filter '{field_name}' is empty."
                )
            if ":" not in item:
                continue
            operator, operand = item.split(":", 1)
            if operator not in allowed:
                raise ValueError(
                    f"Webhook event filter '{field_name}' does not support "
                    f"the '{operator}' operator."
                )
            if not operand:
                raise ValueError(
                    f"Webhook event filter '{field_name}' has an empty "
                    "operand."
                )
            if operator == "oneof":
                try:
                    choices = json.loads(operand)
                except json.JSONDecodeError as error:
                    raise ValueError(
                        f"Webhook event filter '{field_name}' requires a "
                        "JSON-formatted list for 'oneof'."
                    ) from error
                if (
                    not isinstance(choices, list)
                    or not choices
                    or not all(
                        isinstance(choice, str) and choice
                        for choice in choices
                    )
                ):
                    raise ValueError(
                        f"Webhook event filter '{field_name}' requires a "
                        "non-empty JSON list of strings for 'oneof'."
                    )
        return value

    @model_validator(mode="after")
    def validate_filters(self) -> "WebhookTargetEvent":
        """Validate all configured string filters.

        Returns:
            The validated target event.
        """
        prefix_matching_support = self.get_prefix_matching_support()
        for field_name, allow_startswith in prefix_matching_support.items():
            self._validate_filter(
                getattr(self, field_name),
                field_name=field_name,
                allow_startswith=allow_startswith,
            )
        return self


class WebhookConfiguration(YAMLSerializationMixin):
    """Base class for provider-owned webhook configuration."""


class ParsedWebhookEvent(BaseModel):
    """Provider delivery parsed into provider-neutral metadata."""

    event_type: str
    delivery_id: str | None = None
    payload: dict[str, Any]


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

        Raises:
            WebhookPayloadError: If required metadata is malformed.
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
            ValueError: If the configuration is invalid.
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
    ) -> list["WebhookTriggerResponse"]:
        """Return candidates that match one trusted event.

        Args:
            event: The trusted webhook event.
            candidates: Triggers selected by generic orchestration.

        Returns:
            The matching triggers.
        """


def authenticate_hmac_sha256(
    *, body: bytes, headers: Mapping[str, str], secret: str, header: str
) -> None:
    """Authenticate a sha256-prefixed HMAC signature.

    Args:
        body: The exact request body.
        headers: The request headers.
        secret: The signing secret.
        header: The signature header name.

    Raises:
        WebhookAuthenticationError: If the signature is invalid.
    """
    signature = headers.get(header)
    if not signature or not signature.startswith("sha256="):
        raise WebhookAuthenticationError(
            f"Missing or malformed {header} header."
        )
    expected = (
        "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    )
    if not hmac.compare_digest(signature, expected):
        raise WebhookAuthenticationError("Invalid webhook signature.")
