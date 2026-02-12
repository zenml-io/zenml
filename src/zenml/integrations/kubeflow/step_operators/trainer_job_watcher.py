#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""TrainJob status watcher utilities."""

import time
from typing import Any, Dict, Optional, Tuple, Union
from uuid import UUID

from zenml.client import Client
from zenml.enums import ExecutionStatus
from zenml.integrations.kubeflow.step_operators.trainjob_manifest_utils import (
    TRAINJOB_GROUP,
    TRAINJOB_PLURAL,
    TRAINJOB_VERSION,
)
from zenml.logger import get_logger

logger = get_logger(__name__)

_SUCCESS_CONDITIONS = {"succeeded", "complete", "completed"}
_FAILURE_CONDITIONS = {"failed", "failure"}
_SUCCESS_PHASES = {"succeeded", "complete", "completed"}
_FAILURE_PHASES = {"failed", "error", "cancelled"}



class RunStoppedException(Exception):
    """Raised when a step run is stopped."""


def _is_condition_true(value: Union[bool, str]) -> bool:
    """Checks if a condition value means true.

    Args:
        value: The condition value to check.

    Returns:
        True if the value represents a true condition.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return False


def _extract_reason_message(condition: Dict[str, Any]) -> str:
    """Formats a readable reason/message string from a status condition.

    Args:
        condition: The status condition to extract the reason and message from.

    Returns:
        A string containing the reason and message of the condition.
    """
    reason = condition.get("reason")
    message = condition.get("message")
    if reason and message:
        return f"reason={reason}, message={message}"
    if reason:
        return f"reason={reason}"
    if message:
        return f"message={message}"
    return "no additional details available"


def get_terminal_trainjob_status(
    trainjob: Dict[str, Any],
) -> Optional[Tuple[bool, str]]:
    """Parses terminal TrainJob status from a TrainJob object.

    Args:
        trainjob: TrainJob resource object.

    Returns:
        Tuple `(is_success, message)` if terminal, otherwise `None`.
    """
    status = trainjob.get("status") or {}
    conditions = status.get("conditions") or []

    for condition in conditions:
        condition_type = str(condition.get("type", "")).lower()
        condition_status = condition.get("status")
        if not _is_condition_true(condition_status):
            continue

        details = _extract_reason_message(condition)
        if condition_type in _SUCCESS_CONDITIONS:
            return True, details
        if condition_type in _FAILURE_CONDITIONS:
            return False, details

    phase = status.get("phase")
    if phase:
        normalized_phase = str(phase).lower()
        if normalized_phase in _SUCCESS_PHASES:
            return True, f"phase={phase}"
        if normalized_phase in _FAILURE_PHASES:
            return False, f"phase={phase}"

    return None


def wait_for_trainjob_to_finish(
    custom_objects_api: Any,
    namespace: str,
    name: str,
    poll_interval_seconds: float,
    step_run_id: UUID,
    timeout_seconds: Optional[int] = None,
) -> Dict[str, Any]:
    """Waits for a TrainJob to complete.

    Args:
        step_run_id: ID of the step run.
        custom_objects_api: Kubernetes `CustomObjectsApi` instance.
        namespace: Namespace of the TrainJob.
        name: Name of the TrainJob.
        poll_interval_seconds: Poll interval for status checks.
        timeout_seconds: Optional timeout.

    Raises:
        TimeoutError: If waiting for completion times out.
        RuntimeError: If the TrainJob reaches a terminal failure state.

    Returns:
        The final TrainJob resource.
    """
    start_time = time.time()

    while True:
        step_run_status = Client().get_run_step(step_run_id)
        if step_run_status.status == ExecutionStatus.CANCELLING:
            raise RunStoppedException("Step run was cancelled, cancelling TrainJob.")
        trainjob = custom_objects_api.get_namespaced_custom_object(
            group=TRAINJOB_GROUP,
            version=TRAINJOB_VERSION,
            namespace=namespace,
            plural=TRAINJOB_PLURAL,
            name=name,
        )

        if terminal_status := get_terminal_trainjob_status(trainjob):
            is_success, details = terminal_status
            if is_success:
                logger.info("TrainJob `%s` completed successfully.", name)
                return trainjob
            raise RuntimeError(f"TrainJob `{name}` failed: {details}")

        if timeout_seconds is not None:
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                raise TimeoutError(
                    f"Waiting for TrainJob `{name}` timed out after "
                    f"{timeout_seconds} seconds."
                )

        time.sleep(poll_interval_seconds)


def cancel_trainjob(
    custom_objects_api: Any,
    namespace: str,
    name: str,
) -> None:
    """Suspends a running TrainJob.

    Args:
        custom_objects_api: Kubernetes `CustomObjectsApi` instance.
        namespace: Namespace of the TrainJob.
        name: Name of the TrainJob.
    """
    custom_objects_api.patch_namespaced_custom_object(
        group=TRAINJOB_GROUP,
        version=TRAINJOB_VERSION,
        namespace=namespace,
        plural=TRAINJOB_PLURAL,
        name=name,
        body={"spec": {"suspend": True}},
    )