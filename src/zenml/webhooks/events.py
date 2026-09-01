#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Provider-neutral trusted webhook event models."""

from typing import Any
from uuid import UUID

from zenml.dispatcher import Event


class WebhookEvent(Event):
    """Trusted immutable event handed to registered handlers."""

    project_id: UUID
    webhook_id: UUID
    webhook_type: str
    event_type: str
    delivery_id: str | None = None
    payload: dict[str, Any]
