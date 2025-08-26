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
"""Event system for ZenML pipeline serving with streaming support."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from zenml.logger import get_logger

logger = get_logger(__name__)


class EventType(str, Enum):
    """Types of events that can be emitted during pipeline execution."""

    # Pipeline-level events
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_COMPLETED = "pipeline_completed"
    PIPELINE_FAILED = "pipeline_failed"

    # Step-level events
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"

    # Progress and status events
    PROGRESS_UPDATE = "progress_update"
    STATUS_UPDATE = "status_update"

    # Logging and output events
    LOG = "log"
    OUTPUT = "output"
    ERROR = "error"

    # System events
    HEARTBEAT = "heartbeat"
    CANCELLATION_REQUESTED = "cancellation_requested"

    # Agent-specific events (for future multi-agent support)
    AGENT_MESSAGE = "agent_message"
    TOOL_CALL = "tool_call"
    TOKEN_DELTA = "token_delta"  # For streaming LLM outputs


class LogLevel(str, Enum):
    """Log levels for log events."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ServingEvent(BaseModel):
    """Base event model for pipeline serving events."""

    event_type: EventType = Field(..., description="Type of the event")
    job_id: str = Field(..., description="Job ID this event belongs to")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the event occurred",
    )
    data: Dict[str, Any] = Field(
        default_factory=dict, description="Event-specific data"
    )

    # Optional fields for specific event types
    step_name: Optional[str] = Field(
        None, description="Step name for step-level events"
    )
    level: Optional[LogLevel] = Field(
        None, description="Log level for log events"
    )
    message: Optional[str] = Field(None, description="Human-readable message")
    error: Optional[str] = Field(
        None, description="Error message for error events"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization."""
        return {
            "event_type": self.event_type.value,
            "job_id": self.job_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "step_name": self.step_name,
            "level": self.level.value if self.level else None,
            "message": self.message,
            "error": self.error,
        }


class EventBuilder:
    """Builder class for creating properly formatted serving events."""

    def __init__(self, job_id: str):
        """Initialize event builder for a specific job.

        Args:
            job_id: Job ID for all events created by this builder
        """
        self.job_id = job_id

    def pipeline_started(
        self, pipeline_name: str, parameters: Dict[str, Any], **kwargs
    ) -> ServingEvent:
        """Create a pipeline started event.

        Args:
            pipeline_name: Name of the pipeline
            parameters: Pipeline parameters
            **kwargs: Additional data

        Returns:
            ServingEvent for pipeline start
        """
        return ServingEvent(
            event_type=EventType.PIPELINE_STARTED,
            job_id=self.job_id,
            message=f"Pipeline '{pipeline_name}' started",
            data={
                "pipeline_name": pipeline_name,
                "parameters": parameters,
                **kwargs,
            },
        )

    def pipeline_completed(
        self,
        pipeline_name: str,
        execution_time: float,
        result: Any = None,
        steps_executed: int = 0,
        **kwargs,
    ) -> ServingEvent:
        """Create a pipeline completed event.

        Args:
            pipeline_name: Name of the pipeline
            execution_time: Total execution time in seconds
            result: Pipeline execution result
            steps_executed: Number of steps executed
            **kwargs: Additional data

        Returns:
            ServingEvent for pipeline completion
        """
        return ServingEvent(
            event_type=EventType.PIPELINE_COMPLETED,
            job_id=self.job_id,
            message=f"Pipeline '{pipeline_name}' completed in {execution_time:.2f}s",
            data={
                "pipeline_name": pipeline_name,
                "execution_time": execution_time,
                "result": result,
                "steps_executed": steps_executed,
                **kwargs,
            },
        )

    def pipeline_failed(
        self,
        pipeline_name: str,
        error: str,
        execution_time: Optional[float] = None,
        failed_step: Optional[str] = None,
        **kwargs,
    ) -> ServingEvent:
        """Create a pipeline failed event.

        Args:
            pipeline_name: Name of the pipeline
            error: Error message
            execution_time: Execution time before failure
            failed_step: Step where failure occurred
            **kwargs: Additional data

        Returns:
            ServingEvent for pipeline failure
        """
        return ServingEvent(
            event_type=EventType.PIPELINE_FAILED,
            job_id=self.job_id,
            message=f"Pipeline '{pipeline_name}' failed",
            error=error,
            data={
                "pipeline_name": pipeline_name,
                "execution_time": execution_time,
                "failed_step": failed_step,
                **kwargs,
            },
        )

    def step_started(self, step_name: str, **kwargs) -> ServingEvent:
        """Create a step started event.

        Args:
            step_name: Name of the step
            **kwargs: Additional data

        Returns:
            ServingEvent for step start
        """
        return ServingEvent(
            event_type=EventType.STEP_STARTED,
            job_id=self.job_id,
            step_name=step_name,
            message=f"Step '{step_name}' started",
            data=kwargs,
        )

    def step_completed(
        self,
        step_name: str,
        execution_time: float,
        output: Any = None,
        **kwargs,
    ) -> ServingEvent:
        """Create a step completed event.

        Args:
            step_name: Name of the step
            execution_time: Step execution time in seconds
            output: Step output (may be omitted if large)
            **kwargs: Additional data

        Returns:
            ServingEvent for step completion
        """
        return ServingEvent(
            event_type=EventType.STEP_COMPLETED,
            job_id=self.job_id,
            step_name=step_name,
            message=f"Step '{step_name}' completed in {execution_time:.2f}s",
            data={
                "execution_time": execution_time,
                "output": output,
                **kwargs,
            },
        )

    def step_failed(
        self,
        step_name: str,
        error: str,
        execution_time: Optional[float] = None,
        **kwargs,
    ) -> ServingEvent:
        """Create a step failed event.

        Args:
            step_name: Name of the step
            error: Error message
            execution_time: Execution time before failure
            **kwargs: Additional data

        Returns:
            ServingEvent for step failure
        """
        return ServingEvent(
            event_type=EventType.STEP_FAILED,
            job_id=self.job_id,
            step_name=step_name,
            message=f"Step '{step_name}' failed",
            error=error,
            data={"execution_time": execution_time, **kwargs},
        )

    def log(
        self,
        level: LogLevel,
        message: str,
        step_name: Optional[str] = None,
        **kwargs,
    ) -> ServingEvent:
        """Create a log event.

        Args:
            level: Log level
            message: Log message
            step_name: Optional step name if step-specific
            **kwargs: Additional data

        Returns:
            ServingEvent for log message
        """
        return ServingEvent(
            event_type=EventType.LOG,
            job_id=self.job_id,
            step_name=step_name,
            level=level,
            message=message,
            data=kwargs,
        )

    def error(
        self, error: str, step_name: Optional[str] = None, **kwargs
    ) -> ServingEvent:
        """Create an error event.

        Args:
            error: Error message
            step_name: Optional step name if step-specific
            **kwargs: Additional data

        Returns:
            ServingEvent for error
        """
        return ServingEvent(
            event_type=EventType.ERROR,
            job_id=self.job_id,
            step_name=step_name,
            error=error,
            message=f"Error: {error}",
            data=kwargs,
        )

    def progress_update(
        self,
        current_step: int,
        total_steps: int,
        current_step_name: str,
        progress_percent: Optional[float] = None,
        **kwargs,
    ) -> ServingEvent:
        """Create a progress update event.

        Args:
            current_step: Current step number (1-indexed)
            total_steps: Total number of steps
            current_step_name: Name of the current step
            progress_percent: Optional overall progress percentage
            **kwargs: Additional data

        Returns:
            ServingEvent for progress update
        """
        if progress_percent is None:
            progress_percent = (current_step / total_steps) * 100

        return ServingEvent(
            event_type=EventType.PROGRESS_UPDATE,
            job_id=self.job_id,
            message=f"Progress: {current_step}/{total_steps} steps ({progress_percent:.1f}%)",
            data={
                "current_step": current_step,
                "total_steps": total_steps,
                "current_step_name": current_step_name,
                "progress_percent": progress_percent,
                **kwargs,
            },
        )

    def heartbeat(self, **kwargs) -> ServingEvent:
        """Create a heartbeat event to keep connections alive.

        Args:
            **kwargs: Additional data

        Returns:
            ServingEvent for heartbeat
        """
        return ServingEvent(
            event_type=EventType.HEARTBEAT,
            job_id=self.job_id,
            message="Heartbeat",
            data=kwargs,
        )

    def cancellation_requested(
        self, reason: Optional[str] = None
    ) -> ServingEvent:
        """Create a cancellation requested event.

        Args:
            reason: Optional reason for cancellation

        Returns:
            ServingEvent for cancellation request
        """
        return ServingEvent(
            event_type=EventType.CANCELLATION_REQUESTED,
            job_id=self.job_id,
            message="Cancellation requested",
            data={"reason": reason} if reason else {},
        )


def create_event_builder(job_id: str) -> EventBuilder:
    """Create an event builder for a specific job.

    Args:
        job_id: Job ID for events

    Returns:
        EventBuilder instance
    """
    return EventBuilder(job_id)
