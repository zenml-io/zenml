#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Endpoint definitions for steps (and artifacts) of pipeline runs."""

from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends

from zenml.constants import (
    API,
    INPUTS,
    OUTPUTS,
    STATUS,
    STEP_CONFIGURATION,
    STEPS,
    VERSION_1,
)
from zenml.enums import ExecutionStatus
from zenml.models.pipeline_models import ArtifactModel, StepRunModel
from zenml.zen_server.auth import authorize
from zenml.zen_server.utils import error_response, handle_exceptions, zen_store

router = APIRouter(
    prefix=API + VERSION_1 + STEPS,
    tags=["steps"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


@router.get(
    "/{step_id}",
    response_model=StepRunModel,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_step(step_id: UUID) -> StepRunModel:
    """Get one specific step.

    Args:
        step_id: ID of the step to get.

    Returns:
        The step.
    """
    return zen_store().get_run_step(step_id)


@router.get(
    "/{step_id}" + OUTPUTS,
    response_model=Dict[str, ArtifactModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_step_outputs(step_id: UUID) -> Dict[str, ArtifactModel]:
    """Get the outputs of a specific step.

    Args:
        step_id: ID of the step for which to get the outputs.

    Returns:
        All outputs of the step, mapping from output name to artifact model.
    """
    return zen_store().get_run_step_outputs(step_id)


@router.get(
    "/{step_id}" + INPUTS,
    response_model=Dict[str, ArtifactModel],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_step_inputs(step_id: UUID) -> Dict[str, ArtifactModel]:
    """Get the inputs of a specific step.

    Args:
        step_id: ID of the step for which to get the inputs.

    Returns:
        All inputs of the step, mapping from input name to artifact model.
    """
    return zen_store().get_run_step_inputs(step_id)


@router.get(
    "/{step_id}" + STEP_CONFIGURATION,
    response_model=Dict[str, Any],
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_step_configuration(step_id: UUID) -> Dict[str, Any]:
    """Get the configuration of a specific step.

    Args:
        step_id: ID of the step to get.

    Returns:
        The step configuration.
    """
    return zen_store().get_run_step(step_id).step_configuration


@router.get(
    "/{step_id}" + STATUS,
    response_model=ExecutionStatus,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def get_step_status(step_id: UUID) -> ExecutionStatus:
    """Get the status of a specific step.

    Args:
        step_id: ID of the step for which to get the status.

    Returns:
        The status of the step.
    """
    return zen_store().get_run_step_status(step_id)
