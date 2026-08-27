#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Provider-neutral trusted webhook event models."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from zenml.enums import WebhookType


class WebhookEvent(BaseModel):
    """Trusted immutable event handed to registered consumers."""

    model_config = ConfigDict(frozen=True)

    project_id: UUID
    webhook_id: UUID
    webhook_type: WebhookType
    event_type: str
    delivery_id: str | None = None
    payload: dict[str, Any]
