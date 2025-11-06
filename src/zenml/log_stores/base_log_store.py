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
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, cast

from zenml.enums import StackComponentType
from zenml.stack import Flavor, StackComponent, StackComponentConfig

if TYPE_CHECKING:
    from zenml.logging.step_logging import LogEntry
    from zenml.models import LogsRequest, LogsResponse


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

    # TODO: This should probably accept not just requests but also responses
    @abstractmethod
    def activate(self, log_request: "LogsRequest") -> None:
        """Activate the log store for log collection.

        This method is called when ZenML needs to start collecting and storing
        logs during pipeline or step execution. It should set up any necessary
        handlers, threads, or connections.

        Args:
            log_request: The log request model.
        """

    @abstractmethod
    def deactivate(self) -> None:
        """Deactivate the log store and stop log collection.

        This method is called when ZenML needs to stop collecting logs.
        It should clean up handlers, flush any pending logs, and shut down
        any background threads or connections.
        """

    def emit(self, record: logging.LogRecord) -> None:
        """Process a log record from the routing handler.

        This method is called by the ZenML routing handler for each log
        record that should be stored by this log store. Implementations
        should process the record according to their backend's requirements.

        The default implementation does nothing. This allows log stores that
        only need to collect logs during pipeline execution (via activate/
        deactivate) without real-time processing to skip implementing this.

        Args:
            record: The Python logging record to process.
        """
        # Default: do nothing
        # This is NOT abstract, so implementations can opt-in
        pass


    @abstractmethod
    def fetch(
        self,
        logs_model: "LogsResponse",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 20000,
    ) -> List["LogEntry"]:
        """Fetch logs from the log store.

        This method is called from the server to retrieve logs for display
        on the dashboard or via API. The implementation should not require
        any integration-specific SDKs that aren't available on the server.

        Each log store implementation can extract the information it needs
        from logs_model:
        - DefaultLogStore: uses logs_model.uri and logs_model.artifact_store_id
        - OtelLogStore: uses logs_model.pipeline_run_id, step_run_id, source
        - DatadogLogStore: uses logs_model.pipeline_run_id, step_run_id, source

        Args:
            logs_model: The logs model containing metadata about the logs.
            start_time: Filter logs after this time.
            end_time: Filter logs before this time.
            limit: Maximum number of log entries to return.

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
