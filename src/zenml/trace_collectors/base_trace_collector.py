#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Base class for all ZenML trace collectors."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, cast

from zenml.enums import StackComponentType
from zenml.stack import Flavor, StackComponent
from zenml.stack.stack_component import StackComponentConfig
from zenml.trace_collectors.models import (
    Session,
    Span,
    Trace,
    TraceAnnotation,
)


class BaseTraceCollectorConfig(StackComponentConfig):
    """Base config for trace collectors."""


class BaseTraceCollector(StackComponent, ABC):
    """Base class for all ZenML trace collectors.

    Trace collectors provide observability into LLM applications by collecting
    and querying traces, spans, and sessions from observability platforms.
    """

    @property
    def config(self) -> BaseTraceCollectorConfig:
        """Returns the config of the trace collector.

        Returns:
            The config of the trace collector.
        """
        return cast(BaseTraceCollectorConfig, self._config)

    @abstractmethod
    def get_session(self, session_id: str) -> List[Trace]:
        """Get all traces for a session.

        Args:
            session_id: The session ID to retrieve traces for.

        Returns:
            List of traces belonging to the session.
        """

    @abstractmethod
    def get_trace(self, trace_id: str) -> Trace:
        """Get a single trace by ID.

        Args:
            trace_id: The trace ID to retrieve.

        Returns:
            The trace with complete information including latency, cost,
            metadata, and annotations.
        """

    @abstractmethod
    def get_traces(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        name: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        **kwargs: Any,
    ) -> List[Trace]:
        """Get traces with optional filtering.

        Args:
            start_time: Filter traces created after this timestamp.
            end_time: Filter traces created before this timestamp.
            session_id: Filter by session ID.
            user_id: Filter by user ID.
            tags: Filter by tags (traces must have all specified tags).
            name: Filter by trace name.
            limit: Maximum number of traces to return.
            offset: Number of traces to skip for pagination.
            **kwargs: Additional provider-specific filter parameters.

        Returns:
            List of traces matching the filters.
        """

    @abstractmethod
    def get_span(self, span_id: str) -> Span:
        """Get a single span by ID.

        Args:
            span_id: The span ID to retrieve.

        Returns:
            The span with complete information.
        """

    @abstractmethod
    def add_annotations(
        self,
        trace_id: str,
        annotations: List[TraceAnnotation],
    ) -> None:
        """Add annotations to a trace.

        Args:
            trace_id: The trace ID to add annotations to.
            annotations: List of annotations to add.
        """

    @abstractmethod
    def log_metadata(
        self,
        trace_id: str,
        metadata: Dict[str, Any],
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Add metadata and tags to a trace.

        Args:
            trace_id: The trace ID to add metadata to.
            metadata: Dictionary of metadata to add.
            tags: List of tags to add.
            **kwargs: Additional provider-specific parameters.
        """

    def get_sessions(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        **kwargs: Any,
    ) -> List[Session]:
        """Get sessions with optional filtering.

        Args:
            limit: Maximum number of sessions to return.
            offset: Number of sessions to skip for pagination.
            **kwargs: Additional provider-specific filter parameters.

        Returns:
            List of sessions matching the filters.
        """
        # Default implementation - can be overridden by subclasses
        raise NotImplementedError(
            "This trace collector does not support session retrieval."
        )

    def search_traces(
        self,
        query: str,
        limit: Optional[int] = None,
        **kwargs: Any,
    ) -> List[Trace]:
        """Search traces by text query.

        Args:
            query: Text to search for in trace content.
            limit: Maximum number of traces to return.
            **kwargs: Additional provider-specific search parameters.

        Returns:
            List of traces matching the search query.
        """
        # Default implementation - can be overridden by subclasses
        raise NotImplementedError(
            "This trace collector does not support text search."
        )


class BaseTraceCollectorFlavor(Flavor):
    """Base class for all ZenML trace collector flavors."""

    @property
    def type(self) -> StackComponentType:
        """Type of the flavor.

        Returns:
            StackComponentType: The type of the flavor.
        """
        return StackComponentType.TRACE_COLLECTOR

    @property
    def config_class(self) -> Type[BaseTraceCollectorConfig]:
        """Config class for this flavor.

        Returns:
            The config class for this flavor.
        """
        return BaseTraceCollectorConfig

    @property
    @abstractmethod
    def implementation_class(self) -> Type[StackComponent]:
        """Returns the implementation class for this flavor.

        Returns:
            The implementation class for this flavor.
        """
        return BaseTraceCollector
