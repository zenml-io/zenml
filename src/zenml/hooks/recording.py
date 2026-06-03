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
"""Hook invocation recording."""

import os
from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)
from uuid import UUID, uuid4

from zenml.artifacts.utils import _store_artifact_data_and_prepare_request
from zenml.client import Client
from zenml.enums import ArtifactSaveType, ExecutionStatus, HookType
from zenml.models import (
    ExceptionInfo,
    HookInvocationRequest,
    HookInvocationResponse,
)
from zenml.utils import string_utils
from zenml.utils.time_utils import utc_now


def _hook_output_uri(
    artifact_store_path: str,
    pipeline_run_id: UUID,
    hook_invocation_id: UUID,
    output_name: str,
) -> str:
    """Build the artifact URI for a hook output.

    Args:
        artifact_store_path: The path of the active artifact store.
        pipeline_run_id: The pipeline run the hook invocation belongs to.
        hook_invocation_id: The hook invocation the output belongs to.
        output_name: The name of the output.

    Returns:
        The artifact URI.
    """
    output_name = string_utils.sanitize_uri_path_component(output_name)
    return os.path.join(
        artifact_store_path,
        str(pipeline_run_id),
        str(hook_invocation_id),
        output_name,
    )


def _materialize_hook_outputs(
    outputs: Dict[str, Any],
    pipeline_run_id: UUID,
    hook_invocation_id: UUID,
) -> Dict[str, List[UUID]]:
    """Materialize hook outputs as artifact versions.

    Args:
        outputs: Mapping of output names to values.
        pipeline_run_id: The pipeline run the hook invocation belongs to.
        hook_invocation_id: The hook invocation the outputs belong to.

    Returns:
        Mapping of output names to the created artifact version IDs.
    """
    if not outputs:
        return {}

    from zenml.materializers.materializer_registry import (
        materializer_registry,
    )

    client = Client()
    artifact_store = client.active_stack.artifact_store

    artifact_requests = []
    for output_name, value in outputs.items():
        materializer_class = materializer_registry[type(value)]
        uri = _hook_output_uri(
            artifact_store_path=artifact_store.path,
            pipeline_run_id=pipeline_run_id,
            hook_invocation_id=hook_invocation_id,
            output_name=output_name,
        )
        artifact_requests.append(
            _store_artifact_data_and_prepare_request(
                data=value,
                name=output_name,
                uri=uri,
                materializer_class=materializer_class,
                save_type=ArtifactSaveType.MANUAL,
                artifact_store=artifact_store,
            )
        )

    responses = client.zen_store.batch_create_artifact_versions(
        artifact_requests
    )
    return {
        output_name: [response.id]
        for output_name, response in zip(outputs.keys(), responses)
    }


def _resolve_hook_context() -> Tuple[UUID, Optional[UUID]]:
    """Resolve the pipeline run and step run IDs from the active context.

    Raises:
        RuntimeError: If there is no active step or pipeline run context.

    Returns:
        The pipeline run ID and the optional step run ID.
    """
    from zenml.execution.pipeline.dynamic.run_context import (
        DynamicPipelineRunContext,
    )
    from zenml.steps.step_context import StepContext

    step_context = StepContext.get()
    if step_context is not None:
        return step_context.pipeline_run.id, step_context.step_run.id

    run_context = DynamicPipelineRunContext.get()
    if run_context is not None:
        return run_context.run.id, None

    raise RuntimeError(
        "Recording a hook invocation requires an active pipeline run context. "
        "It can only be called from inside a step or a dynamic pipeline."
    )


def record_hook_invocation(
    name: Optional[str] = None,
    hook_type: HookType = HookType.CUSTOM,
    source: Optional[str] = None,
    outputs: Optional[Dict[str, Any]] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    status: ExecutionStatus = ExecutionStatus.COMPLETED,
    exception_info: Optional[ExceptionInfo] = None,
    logs_id: Optional[UUID] = None,
) -> HookInvocationResponse:
    """Record a hook invocation for an already-completed event.

    Args:
        name: Custom event name for the invocation.
        hook_type: Type of the hook invocation.
        source: Resolved source of the hook function.
        outputs: Output values to materialize as artifacts.
        start_time: Start time of the event.
        end_time: End time of the event.
        status: Terminal status of the event.
        exception_info: Exception information when the event failed.
        logs_id: ID of the logs entry to link to the invocation.

    Returns:
        The recorded hook invocation.
    """
    pipeline_run_id, step_run_id = _resolve_hook_context()

    hook_invocation_id = uuid4()
    now = utc_now()

    materialized_outputs = _materialize_hook_outputs(
        outputs=outputs or {},
        pipeline_run_id=pipeline_run_id,
        hook_invocation_id=hook_invocation_id,
    )

    client = Client()
    request = HookInvocationRequest(
        id=hook_invocation_id,
        project=client.active_project.id,
        hook_type=hook_type,
        name=name,
        status=status,
        start_time=start_time or now,
        end_time=end_time or now,
        source=source,
        pipeline_run_id=pipeline_run_id,
        step_run_id=step_run_id,
        outputs=materialized_outputs,
        exception_info=exception_info,
        logs_id=logs_id,
    )
    return client.zen_store.create_hook_invocation(request)
