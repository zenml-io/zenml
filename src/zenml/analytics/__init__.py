#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""The 'analytics' module of ZenML."""
from contextvars import ContextVar
from typing import Any, Dict, Optional, TYPE_CHECKING
from uuid import UUID

from zenml.enums import SourceContextTypes

if TYPE_CHECKING:
    from zenml.analytics.enums import AnalyticsEvent

source_context: ContextVar[SourceContextTypes] = ContextVar(
    "Source-Context", default=SourceContextTypes.PYTHON
)


def identify(  # type: ignore[return]
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """Attach metadata to user directly.

    Args:
        metadata: Dict of metadata to attach to the user.

    Returns:
        True if event is sent successfully, False is not.
    """
    from zenml.analytics.context import AnalyticsContext

    if metadata is None:
        return False

    with AnalyticsContext() as analytics:
        return analytics.identify(traits=metadata)


def alias(user_id: UUID, previous_id: UUID) -> bool:  # type: ignore[return]
    """Alias user IDs.

    Args:
        user_id: The user ID.
        previous_id: Previous ID for the alias.

    Returns:
        True if event is sent successfully, False is not.
    """
    from zenml.analytics.context import AnalyticsContext

    with AnalyticsContext() as analytics:
        return analytics.alias(user_id=user_id, previous_id=previous_id)


def group(  # type: ignore[return]
    group_id: UUID,
    group_metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """Attach metadata to a segment group.

    Args:
        group_id: ID of the group.
        group_metadata: Metadata to attach to the group.

    Returns:
        True if event is sent successfully, False if not.
    """
    from zenml.analytics.context import AnalyticsContext

    with AnalyticsContext() as analytics:
        return analytics.group(group_id=group_id, traits=group_metadata)


def track(  # type: ignore[return]
    event: "AnalyticsEvent",
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """Track segment event if user opted-in.

    Args:
        event: Name of event to track in segment.
        metadata: Dict of metadata to track.

    Returns:
        True if event is sent successfully, False if not.
    """
    from zenml.analytics.context import AnalyticsContext

    if metadata is None:
        metadata = {}

    metadata.setdefault("event_success", True)

    with AnalyticsContext() as analytics:
        return analytics.track(event=event, properties=metadata)
