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

from typing import TYPE_CHECKING, Optional

from zenml.client import Client
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.trace_collectors.base_trace_collector import BaseTraceCollector

logger = get_logger(__name__)


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


def get_trace_id_from_step_context(
    trace_id_key: str = "trace_id",
) -> Optional[str]:
    """Get the trace ID from the current step context metadata.

    This function should be called from within a step to get the trace ID
    that was set up by the trace collector during pipeline initialization.

    Args:
        trace_id_key: The metadata key to look for the trace ID. Different trace
                     collectors may use different key names (e.g., "langfuse_trace_id").

    Returns:
        The trace ID if available, None otherwise.

    Raises:
        RuntimeError: If called outside of a step context.
    """
    try:
        from zenml.steps import get_step_context

        context = get_step_context()
        pipeline_run = context.pipeline_run

        # Look for trace collector metadata in the pipeline run
        run_metadata = pipeline_run.run_metadata

        # Search for trace collector component metadata
        trace_collector = get_trace_collector()
        component_id = trace_collector.id

        if component_id in run_metadata:
            component_metadata = run_metadata[component_id]
            if isinstance(component_metadata, dict):
                trace_id = component_metadata.get(trace_id_key)
                if trace_id:
                    logger.debug(
                        f"Retrieved trace ID from step context: {trace_id}"
                    )
                    return trace_id

        # Fallback: look directly in run_metadata
        trace_id = run_metadata.get(trace_id_key)
        if trace_id:
            logger.debug(
                f"Retrieved trace ID from direct metadata: {trace_id}"
            )
            return trace_id

        logger.debug(
            f"No trace ID found in step context metadata with key '{trace_id_key}'"
        )
        return None

    except Exception as e:
        logger.warning(f"Failed to get trace ID from step context: {e}")
        return None


def get_trace_url_from_step_context(
    url_key: str = "trace_url",
) -> Optional[str]:
    """Get a trace URL from the current step context metadata.

    Args:
        url_key: The metadata key to look for the trace URL. Different trace
                collectors may use different key names.

    Returns:
        The trace URL if available, None otherwise.
    """
    try:
        from zenml.steps import get_step_context

        context = get_step_context()
        pipeline_run = context.pipeline_run
        run_metadata = pipeline_run.run_metadata

        # Search for trace collector component metadata
        trace_collector = get_trace_collector()
        component_id = trace_collector.id

        if component_id in run_metadata:
            component_metadata = run_metadata[component_id]
            if isinstance(component_metadata, dict):
                trace_url = component_metadata.get(url_key)
                if trace_url:
                    return str(trace_url)

        # Fallback: look directly in run_metadata
        trace_url = run_metadata.get(url_key)
        if trace_url:
            return str(trace_url)

        return None

    except Exception as e:
        logger.warning(f"Failed to get trace URL from step context: {e}")
        return None
