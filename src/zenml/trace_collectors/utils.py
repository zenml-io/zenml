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
"""Trace collector utilities."""

from typing import TYPE_CHECKING

from zenml.client import Client

if TYPE_CHECKING:
    from zenml.trace_collectors.base_trace_collector import BaseTraceCollector


def get_trace_collector() -> "BaseTraceCollector":
    """Get the trace collector from the active stack.

    Returns:
        The active trace collector.

    Raises:
        RuntimeError: If no trace collector is configured in the active stack.
    """
    trace_collector = Client().active_stack.trace_collector

    if not trace_collector:
        raise RuntimeError(
            "Unable to get trace collector: Missing trace collector in the "
            "active stack. To solve this, register a trace collector and "
            "add it to your stack. See the ZenML documentation for more "
            "information."
        )

    return trace_collector
