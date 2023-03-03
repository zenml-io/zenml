from abc import abstractmethod
from typing import Any, Dict
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.analytics.constants import TRACK, IDENTIFY, GROUP
from zenml.utils.analytics_utils import AnalyticsEvent
import analytics


class AnalyticsRequest(BaseModel):
    @abstractmethod
    def track(self, key):
        """"""


class TrackRequest(BaseModel):
    """Base model for track requests.

    Attributes:
        user_id: the canonical ID of the user.
        event: the type of the event.
        properties: the metadata about the event.
    """

    type: str = Field(TRACK, const=True)

    user_id: UUID
    event: AnalyticsEvent
    properties: Dict[Any, Any]

    def track(self, key):
        client = analytics.Client(
            write_key=key,
            max_retries=1,
        )
        client.track(
            user_id=str(self.user_id),
            event=str(self.event.value),
            properties=self.properties,
        )


class GroupRequest(BaseModel):
    """Base Model for group requests.

    Attributes:
        user_id: the canonical ID of the user.
        group_id: the ID of the group.
        traits: traits of the group.
    """

    type: str = Field(GROUP, const=True)

    user_id: UUID
    group_id: UUID
    traits: Dict[Any, Any]

    def track(self, key):
        client = analytics.Client(
            write_key=key,
            max_retries=1,
        )

        client.group(
            user_id=str(self.user_id),
            group_id=str(self.group_id),
            traits=self.traits,
        )


class IdentifyRequest(BaseModel):
    """Base model for identify requests.

    Attributes:
        user_id: the canonical ID of the user.
        traits: traits of the identified user.
    """

    type: str = Field(IDENTIFY, const=True)

    user_id: UUID
    traits: Dict[Any, Any]

    def track(self, key):
        client = analytics.Client(
            write_key=key,
            max_retries=1,
        )

        client.identify(
            user_id=str(self.user_id),
            traits=self.traits,
        )
