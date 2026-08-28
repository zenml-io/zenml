#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
"""URL utilities for webhook intake endpoints."""

from uuid import UUID

from zenml.constants import WEBHOOKS
from zenml.enums import WebhookType
from zenml.utils.server_utils import get_server_api_url


def get_webhook_intake_url(
    *, webhook_type: WebhookType | str, webhook_id: UUID
) -> str | None:
    """Build the externally reachable intake URL for a webhook.

    Args:
        webhook_type: The webhook provider type.
        webhook_id: The webhook ID.

    Returns:
        The absolute intake URL, or `None` when no external server URL is
        configured.
    """
    server_api_url = get_server_api_url()
    if server_api_url is None:
        return None
    provider = (
        webhook_type.value
        if isinstance(webhook_type, WebhookType)
        else webhook_type
    )
    return f"{server_api_url}{WEBHOOKS}/{provider}/{webhook_id}/events"
