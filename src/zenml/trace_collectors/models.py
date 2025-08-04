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
"""Data models for trace collection."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class TraceUsage(BaseModel):
    """Usage information for a trace."""

    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    input_cost: Optional[float] = None
    output_cost: Optional[float] = None
    total_cost: Optional[float] = None


class TraceAnnotation(BaseModel):
    """Annotation for a trace or span."""

    id: str
    name: str
    value: Union[str, int, float, bool]
    comment: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class BaseObservation(BaseModel):
    """Base class for all observations (traces, spans, generations, events)."""

    id: str
    name: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    input: Optional[Any] = None
    output: Optional[Any] = None
    tags: List[str] = Field(default_factory=list)
    level: Optional[str] = None
    status_message: Optional[str] = None
    version: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    @property
    def duration_ms(self) -> Optional[float]:
        """Calculate duration in milliseconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return None


class Span(BaseObservation):
    """Represents a span in a trace."""

    trace_id: str
    parent_observation_id: Optional[str] = None
    usage: Optional[TraceUsage] = None


class Generation(BaseObservation):
    """Represents an AI model generation."""

    trace_id: str
    parent_observation_id: Optional[str] = None
    model: Optional[str] = None
    model_parameters: Dict[str, Any] = Field(default_factory=dict)
    usage: Optional[TraceUsage] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


class Event(BaseObservation):
    """Represents a discrete event in a trace."""

    trace_id: str
    parent_observation_id: Optional[str] = None


class Trace(BaseObservation):
    """Represents a complete trace with all its observations."""

    user_id: Optional[str] = None
    session_id: Optional[str] = None
    release: Optional[str] = None
    external_id: Optional[str] = None
    public: bool = False
    bookmarked: bool = False
    usage: Optional[TraceUsage] = None
    observations: List[Union[Span, Generation, Event]] = Field(
        default_factory=list
    )
    annotations: List[TraceAnnotation] = Field(default_factory=list)

    def get_spans(self) -> List[Span]:
        """Get all spans in this trace."""
        return [obs for obs in self.observations if isinstance(obs, Span)]

    def get_generations(self) -> List[Generation]:
        """Get all generations in this trace."""
        return [
            obs for obs in self.observations if isinstance(obs, Generation)
        ]

    def get_events(self) -> List[Event]:
        """Get all events in this trace."""
        return [obs for obs in self.observations if isinstance(obs, Event)]


class Session(BaseModel):
    """Represents a session containing multiple traces."""

    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    public: bool = False
    bookmarked: bool = False
    trace_count_total: int = 0
    user_count_total: int = 0
