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
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, cast

from zenml.enums import StackComponentType
from zenml.models import LogsResponse
from zenml.stack import Flavor, StackComponent, StackComponentConfig
from zenml.utils.logging_utils import LogEntry

MAX_ENTRIES_PER_REQUEST = 20000


class BaseLogStoreConfig(StackComponentConfig):
    """Base configuration for all log stores."""


class BaseLogStoreEmitter:
    """Base class for all ZenML log store emitters.

    The emitter is the entry point for all log records to be emitted to the log
    store. The process of emitting a log record is as follows:

    1. instantiate a BaseLogStoreEmitter
    2. create an emitter by calling log_store.register_emitter() and passing the
    log model and optional metadata to be attached to each log record
    3. emit the log record by calling emitter.emit() and passing the log record
    4. deregister the emitter when all logs have been emitted by calling
    emitter.deregister()
    """

    def __init__(
        self,
        name: str,
        log_store: "BaseLogStore",
        log_model: LogsResponse,
        metadata: Dict[str, Any],
    ) -> None:
        """Initialize a log store emitter.

        Args:
            name: The name of the emitter.
            log_store: The log store to emit logs to.
            log_model: The log model associated with the emitter.
            metadata: Additional metadata to attach to all log entries that will
                be emitted by this emitter.
        """
        self._name = name
        self._log_store = log_store
        self._log_model = log_model
        self._metadata = metadata

    @property
    def name(self) -> str:
        """The name of the emitter.

        Returns:
            The name of the emitter.
        """
        return self._name

    @property
    def log_model(self) -> LogsResponse:
        """The log model associated with the emitter.

        Returns:
            The log model.
        """
        return self._log_model

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to the log store.

        Args:
            record: The log record to emit.
        """
        self._log_store._emit(self, record, metadata=self._metadata)

    def deregister(self) -> None:
        """Deregister the emitter from the log store."""
        self._log_store.deregister_emitter(self)


class BaseLogStore(StackComponent, ABC):
    """Base class for all ZenML log stores.

    A log store is responsible for collecting, storing, and retrieving logs
    during pipeline and step execution. Different implementations may store
    logs in different backends (artifact store, OpenTelemetry, Datadog, etc.).
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the log store.

        Args:
            *args: Positional arguments for the base class.
            **kwargs: Keyword arguments for the base class.
        """
        super().__init__(*args, **kwargs)
        self._emitters: Dict[str, BaseLogStoreEmitter] = {}
        self._lock = threading.RLock()

    @property
    def config(self) -> BaseLogStoreConfig:
        """Returns the configuration of the log store.

        Returns:
            The configuration.
        """
        return cast(BaseLogStoreConfig, self._config)

    @property
    def emitter_class(self) -> Type[BaseLogStoreEmitter]:
        """Class of the emitter.

        Returns:
            The class of the emitter.
        """
        return BaseLogStoreEmitter

    def register_emitter(
        self, name: str, log_model: LogsResponse, metadata: Dict[str, Any]
    ) -> BaseLogStoreEmitter:
        """Register an emitter for the log store.

        Args:
            name: The name of the emitter.
            log_model: The log model associated with the emitter.
            metadata: Additional metadata to attach to the log entry.

        Returns:
            The emitter.
        """
        with self._lock:
            emitter = self.emitter_class(name, self, log_model, metadata)
            self._emitters[name] = emitter
            return emitter

    def deregister_emitter(self, emitter: BaseLogStoreEmitter) -> None:
        """Deregister an emitter registered with the log store.

        Args:
            emitter: The emitter to deregister.
        """
        with self._lock:
            if emitter.name not in self._emitters:
                return
            self._finalize(emitter)
            del self._emitters[emitter.name]
            if len(self._emitters) == 0:
                self.flush(blocking=False)

    @abstractmethod
    def _emit(
        self,
        emitter: BaseLogStoreEmitter,
        record: logging.LogRecord,
        metadata: Dict[str, Any],
    ) -> None:
        """Process a log record from the logging system.

        Args:
            emitter: The emitter used to emit the log record.
            record: The Python logging.LogRecord to process.
            metadata: Additional metadata to attach to the log entry.
        """

    @abstractmethod
    def _finalize(
        self,
        emitter: BaseLogStoreEmitter,
    ) -> None:
        """Finalize the stream of log records associated with an emitter.

        This is used to announce the end of the stream of log records associated
        with an emitter and that no more log records will be emitted.

        The implementation should ensure that all log records associated with
        the emitter are flushed to the backend and any resources (clients,
        connections, file descriptors, etc.) are released.

        Args:
            emitter: The emitter to finalize.
        """

    @abstractmethod
    def flush(self, blocking: bool = True) -> None:
        """Flush the log store.

        This method is called to ensure that all logs are flushed to the backend.

        Args:
            blocking: Whether to block until the flush is complete.
        """

    @abstractmethod
    def fetch(
        self,
        logs_model: LogsResponse,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = MAX_ENTRIES_PER_REQUEST,
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
