#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Base class for log stores."""

import logging
from abc import abstractmethod
from datetime import datetime
from typing import List, Optional, Type, cast

from zenml.enums import StackComponentType
from zenml.log_stores.utils import LogEntry
from zenml.logging.logging import LoggingContext
from zenml.models import LogsResponse
from zenml.stack import Flavor, StackComponent, StackComponentConfig

# Maximum number of log entries to return in a single request
MAX_ENTRIES_PER_REQUEST = 20000
# Maximum size of a single log message in bytes (5KB)
DEFAULT_MESSAGE_SIZE = 5 * 1024


class BaseLogStoreConfig(StackComponentConfig):
    """Base configuration for all log stores."""


class BaseLogStore(StackComponent):
    """Base class for all ZenML log stores.

    A log store is responsible for collecting, storing, and retrieving logs
    during pipeline and step execution. Different implementations may store
    logs in different backends (artifact store, OpenTelemetry, Datadog, etc.).
    """

    @property
    def config(self) -> BaseLogStoreConfig:
        """Returns the configuration of the log store.

        Returns:
            The configuration.
        """
        return cast(BaseLogStoreConfig, self._config)

    @abstractmethod
    def emit(
        self,
        record: logging.LogRecord,
        context: LoggingContext,
    ) -> None:
        """Process a log record from the logging system.

        Args:
            record: The Python logging.LogRecord to process.
            context: The logging context containing the log_model.
        """

    @abstractmethod
    def fetch(
        self,
        logs_model: LogsResponse,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = MAX_ENTRIES_PER_REQUEST,
        message_size: int = DEFAULT_MESSAGE_SIZE,
    ) -> List[LogEntry]:
        """Fetch logs from the log store.

        This method is called from the server to retrieve logs for display
        on the dashboard or via API. The implementation should not require
        any integration-specific SDKs that aren't available on the server.

        Args:
            logs_model: The logs model containing metadata about the logs.
            start_time: Filter logs after this time.
            end_time: Filter logs before this time.
            limit: Maximum number of log entries to return.
            message_size: Maximum size of a single log message in bytes.

        Returns:
            List of log entries matching the query.
        """


class BaseLogStoreFlavor(Flavor):
    """Base class for all ZenML log store flavors."""

    @property
    def type(self) -> StackComponentType:
        """Type of the flavor.

        Returns:
            The type of the flavor.
        """
        return StackComponentType.LOG_STORE

    @property
    def config_class(self) -> Type[BaseLogStoreConfig]:
        """Config class for the base log store flavor.

        Returns:
            The config class.
        """
        return BaseLogStoreConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type["BaseLogStore"]:
        """Implementation class for the base log store flavor.

        Returns:
            The implementation class.
        """
