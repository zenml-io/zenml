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
"""Per-request in-memory buffer for serving pipeline execution.

This module provides a request-scoped buffer using ContextVar that allows
zero-persistence handoff between pipeline steps for millisecond-class latency.
"""

from contextvars import ContextVar
from typing import Any, Dict, Optional

from zenml.logger import get_logger

logger = get_logger(__name__)

# Per-request output buffer - each request gets its own isolated buffer
_request_output_buffer: ContextVar[Dict[str, Dict[str, Any]]] = ContextVar(
    "request_output_buffer", default={}
)


def initialize_request_buffer() -> None:
    """Initialize a fresh buffer for the current request."""
    _request_output_buffer.set({})
    logger.debug("Initialized fresh request buffer")


def store_step_outputs(step_name: str, outputs: Dict[str, Any]) -> None:
    """Store step outputs in the request buffer.

    Args:
        step_name: Name of the step that produced the outputs
        outputs: Dictionary of output_name -> python_value
    """
    buffer = _request_output_buffer.get({})
    buffer[step_name] = outputs.copy()
    _request_output_buffer.set(buffer)

    logger.debug(
        f"Stored outputs for step '{step_name}': {list(outputs.keys())}"
    )


def get_step_outputs(step_name: str) -> Dict[str, Any]:
    """Get outputs from a specific step.

    Args:
        step_name: Name of the step to get outputs from

    Returns:
        Dictionary of output_name -> python_value, or empty dict if not found
    """
    buffer = _request_output_buffer.get({})
    return buffer.get(step_name, {})


def get_all_outputs() -> Dict[str, Dict[str, Any]]:
    """Get all outputs from the request buffer.

    Returns:
        Dictionary of step_name -> {output_name -> python_value}
    """
    return _request_output_buffer.get({}).copy()


def clear_request_buffer() -> None:
    """Clear the request buffer to free memory."""
    _request_output_buffer.set({})
    logger.debug("Cleared request buffer")


def get_pipeline_outputs(
    return_contract: Optional[Dict[str, str]],
) -> Dict[str, Any]:
    """Extract only the declared pipeline outputs from the buffer.

    Args:
        return_contract: Mapping of output_name -> step_name from pipeline function

    Returns:
        Dictionary containing only the declared pipeline outputs
    """
    if not return_contract:
        # No return contract - return all outputs (fallback)
        all_outputs = get_all_outputs()
        result = {}
        for step_name, step_outputs in all_outputs.items():
            for output_name, value in step_outputs.items():
                result[f"{step_name}_{output_name}"] = value
        return result

    # Map return contract to actual outputs
    result = {}
    buffer = _request_output_buffer.get({})

    for output_name, step_name in return_contract.items():
        if step_name in buffer:
            step_outputs = buffer[step_name]
            if step_outputs:
                # Take first output from the step (simplified)
                first_output = next(iter(step_outputs.values()))
                result[output_name] = first_output
            else:
                logger.warning(
                    f"Step '{step_name}' in return contract has no outputs"
                )
        else:
            logger.warning(
                f"Step '{step_name}' from return contract not found in buffer"
            )

    return result
