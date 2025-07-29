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
"""Trace collectors let you collect and query traces from LLM observability platforms.

Trace collectors provide a unified interface to retrieve traces, spans, and sessions
from various LLM observability and tracing platforms. This enables monitoring,
debugging, and analysis of LLM application behavior in ZenML pipelines.
"""

from zenml.trace_collectors.base_trace_collector import (
    BaseTraceCollector,
    BaseTraceCollectorConfig,
    BaseTraceCollectorFlavor,
)
from zenml.trace_collectors.models import (
    BaseObservation,
    Event,
    Generation,
    Session,
    Span,
    Trace,
    TraceAnnotation,
    TraceUsage,
)

__all__ = [
    "BaseTraceCollector",
    "BaseTraceCollectorConfig", 
    "BaseTraceCollectorFlavor",
    "BaseObservation",
    "Event",
    "Generation",
    "Session",
    "Span",
    "Trace",
    "TraceAnnotation",
    "TraceUsage",
]