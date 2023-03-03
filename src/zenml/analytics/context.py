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
import os
from types import TracebackType
from typing import Any, Optional, Dict, Union, Type, List, TYPE_CHECKING
from uuid import UUID

import requests

from zenml import __version__
from zenml.analytics.constants import (
    TRACK_ENDPOINT,
    IDENTIFY_ENDPOINT,
    GROUP_ENDPOINT,
)
from zenml.analytics.models import TrackRequest, GroupRequest, IdentifyRequest
from zenml.constants import ENV_ZENML_SERVER_FLAG, ANALYTICS_SERVER_URL
from zenml.environment import Environment, get_environment
from zenml.logger import get_logger
from zenml.utils.analytics_utils import (
    AnalyticsEvent,
)

if TYPE_CHECKING:
    from zenml.models.server_models import (
        ServerDatabaseType,
        ServerDeploymentType,
    )
Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]

logger = get_logger(__name__)


class AnalyticsContext:
    """Client class for ZenML Analytics v2."""

    def __init__(self) -> None:
        """Initialization.

        Use this as a context manager to ensure that analytics are initialized
        properly, only tracked when configured to do so and that any errors
        are handled gracefully.
        """
        self.analytics_opt_in: bool = False

        self.user_id: Optional[UUID] = None
        self.client_id: Optional[UUID] = None
        self.server_id: Optional[UUID] = None

        self.database_type: Optional["ServerDatabaseType"] = None
        self.deployment_type: Optional["ServerDeploymentType"] = None

    @property
    def in_server(self):
        """Flag to check whether the code is running on the server side."""
        return os.getenv(ENV_ZENML_SERVER_FLAG, False)

    def __enter__(self) -> "AnalyticsContext":
        """Enter analytics context manager.

        Returns:
            self.
        """
        # Fetch the analytics opt-in setting
        from zenml.config.global_config import GlobalConfiguration
        from zenml.zen_server.auth import get_auth_context

        gc = GlobalConfiguration()
        self.analytics_opt_in = gc.analytics_opt_in

        if self.analytics_opt_in:
            try:
                # Fetch the `user_id`
                if self.in_server:
                    # If the code is running on the server side, use the auth context.
                    auth_context = get_auth_context()
                    if auth_context is not None:
                        self.user_id = auth_context.user.id
                else:
                    # If the code is running on the client side, use the default user.
                    default_user = gc.zen_store.get_user()
                    self.user_id = default_user.id

                # Fetch the `client_id`
                if self.in_server:
                    # If the code is running on the server side, there is no client id.
                    self.client_id = None
                else:
                    # If the code is running on the client side, attach the client id.
                    self.client_id = gc.user_id

                # Fetch the store information including the `server_id`
                store_info = gc.zen_store.get_store_info()

                self.server_id = store_info.id
                self.deployment_type = store_info.deployment_type
                self.database_type = store_info.database_type
            except Exception as e:
                self.analytics_opt_in = False
                logger.debug(f"Analytics initialization failed: {e}")
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> bool:
        """Exit context manager.

        Args:
            exc_type: Exception type.
            exc_val: Exception value.
            exc_tb: Exception traceback.

        Returns:
            True if exception was handled, False otherwise.
        """
        if exc_val is not None:
            logger.debug(f"Sending telemetry data failed: {exc_val}")

        return True

    def _post(self, endpoint, payload) -> Json:
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
        }
        return self._handle_response(
            requests.post(
                url=ANALYTICS_SERVER_URL + endpoint,
                headers=headers,
                json=payload.json(),
            )
        )

    def identify(self, traits: Optional[Dict[str, Any]] = None) -> bool:
        """Identify the user through segment.

        Args:
            traits: Traits of the user.

        Returns:
            True if tracking information was sent, False otherwise.
        """

        if self.analytics_opt_in:
            payload = IdentifyRequest(
                user_id=self.user_id,
                traits=traits,
            )
            self._post(endpoint=IDENTIFY_ENDPOINT, payload=payload)

            return True
        return False

    def group(
        self,
        group_id: str,
        traits: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Group the user.

        Args:
            group_id: Group ID.
            traits: Traits of the group.

        Returns:
            True if tracking information was sent, False otherwise.
        """
        if self.analytics_opt_in:
            if traits is None:
                traits = {}

            traits.update({"group_id": group_id})

            payload = GroupRequest(
                user_id=self.user_id,
                group_id=group_id,
                traits=traits,
            )

            self._post(endpoint=GROUP_ENDPOINT, payload=payload)
            return True

        return False

    def track(
        self,
        event: AnalyticsEvent,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Track an event.

        Args:
            event: Event to track.
            properties: Event properties.

        Returns:
            True if tracking information was sent, False otherwise.
        """
        if not isinstance(event, AnalyticsEvent):
            raise ValueError(
                "When tracking events, please provide one of the supported "
                "event types."
            )

        if properties is None:
            properties = {}

        if not self.analytics_opt_in and event.value not in {
            AnalyticsEvent.OPT_OUT_ANALYTICS,
            AnalyticsEvent.OPT_IN_ANALYTICS,
        }:
            return False

        # add basics
        properties.update(Environment.get_system_info())
        properties.update(
            {
                "environment": get_environment(),
                "python_version": Environment.python_version(),
                "version": __version__,
                "client_id": str(self.client_id),
                "user_id": str(self.user_id),
                "server_id": str(self.server_id),
                "deployment_type": str(self.deployment_type),
                "database_type": str(self.database_type),
            }
        )

        for k, v in properties.items():
            if isinstance(v, UUID):
                properties[k] = str(v)

        payload = TrackRequest(
            user_id=self.user_id,
            event=event,
            properties=properties,
        )

        self._post(endpoint=TRACK_ENDPOINT, payload=payload)

        logger.debug(
            f"Analytics sent: User: {self.user_id}, Event: {event}, Metadata: "
            f"{properties}"
        )

        return True

    @staticmethod
    def _handle_response(response: requests.Response) -> Json:
        """Handle API response, translating http status codes to Exception.

        Args:
            response: The response to handle.

        Returns:
            The parsed response.
        """
        if 200 <= response.status_code < 300:
            try:
                payload: Json = response.json()
                return payload
            except requests.exceptions.JSONDecodeError:
                logger.debug(
                    "Bad response from API. Expected json, got\n"
                    f"{response.text}"
                )
        elif response.status_code == 422:
            response_details = response.json().get("detail", (response.text,))
            if isinstance(response_details[0], str):
                response_msg = ": ".join(response_details)
            else:
                # This is an "Unprocessable Entity" error, which has a special
                # structure in the response.
                response_msg = response.text
            raise logger.debug(response_msg)
        else:
            raise logger.debug(
                "Error retrieving from API. Got response "
                f"{response.status_code} with body:\n{response.text}"
            )
