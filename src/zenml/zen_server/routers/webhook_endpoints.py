#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Endpoint definitions for webhooks."""
from typing import Any, Dict

from fastapi import APIRouter
from starlette.background import BackgroundTasks

from zenml.constants import API, VERSION_1, WEBHOOKS
from zenml.enums import PluginSubType
from zenml.event_hub.event_hub import event_hub
from zenml.logger import get_logger
from zenml.zen_server.utils import handle_exceptions

logger = get_logger(__name__)

router = APIRouter(
    prefix=API + VERSION_1 + WEBHOOKS,
    tags=["webhook"],
)


@router.post(
    "/{flavor_name}",
)
@handle_exceptions
def webhook(
    flavor_name: str,
    body: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    """Webhook to receive events from external event sources.

    Args:
        flavor_name: Path param that indicates which plugin flavor will handle the event.
        body: The request body.
        background_tasks: BackgroundTask fixture
    """
    background_tasks.add_task(
        event_hub.process_event,
        incoming_event=body,
        flavor=flavor_name,
        event_source_subtype=PluginSubType.WEBHOOK,
    )
