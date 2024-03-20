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
"""Implementation of the ServiceStatus class."""

from typing import Optional

from zenml.logger import get_logger
from zenml.utils.enum_utils import StrEnum
from zenml.utils.typed_model import BaseTypedModel

logger = get_logger(__name__)


class ServiceState(StrEnum):
    """Possible states for the service and service endpoint."""

    INACTIVE = "inactive"
    ACTIVE = "active"
    PENDING_STARTUP = "pending_startup"
    PENDING_SHUTDOWN = "pending_shutdown"
    ERROR = "error"
    SCALED_TO_ZERO = "scaled_to_zero"


class ServiceStatus(BaseTypedModel):
    """Information about the status of a service or process.

    This information describes the operational status of an external process or
    service tracked by ZenML. This could be a process, container, Kubernetes
    deployment etc.

    Concrete service classes should extend this class and add additional
    attributes that make up the operational state of the service.

    Attributes:
        state: the current operational state
        last_state: the operational state prior to the last status update
        last_error: the error encountered during the last status update
    """

    state: ServiceState = ServiceState.INACTIVE
    last_state: ServiceState = ServiceState.INACTIVE
    last_error: str = ""

    def update_state(
        self,
        new_state: Optional[ServiceState] = None,
        error: str = "",
    ) -> None:
        """Update the current operational state to reflect a new state value and/or error.

        Args:
            new_state: new operational state discovered by the last service
                status update
            error: error message describing an operational failure encountered
                during the last service status update
        """
        if new_state and self.state != new_state:
            self.last_state = self.state
            self.state = new_state
        if error:
            self.last_error = error

    def clear_error(self) -> None:
        """Clear the last error message."""
        self.last_error = ""
