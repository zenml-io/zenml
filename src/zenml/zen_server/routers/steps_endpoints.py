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
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException

from zenml.constants import OUTPUTS, STEPS, VERSION_1
from zenml.models.pipeline_models import StepRunModel
from zenml.zen_server.utils import (
    authorize,
    error_detail,
    error_response,
    not_found,
    zen_store,
)

router = APIRouter(
    prefix=VERSION_1 + STEPS,
    tags=["steps"],
    dependencies=[Depends(authorize)],
    responses={401: error_response},
)


@router.get(
    "/{step_id}",
    response_model=Dict,
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_step(step_id: str) -> StepRunModel:
    """Get one specific step.

    Args:
        step_id: ID of the step to get.

    Returns:
        The step.

    Raises:
        not_found: If the step does not exist.
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_run_step(step_id)
    except KeyError as e:
        raise not_found(e) from e
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))


@router.get(
    "/{step_id}" + OUTPUTS,
    response_model=List[Dict],
    responses={401: error_response, 404: error_response, 422: error_response},
)
async def get_step_outputs(step_id: str) -> List[Dict]:
    """Get a list of outputs for a specific step.

    Args:
        step_id: ID of the step for which to get the outputs.

    Returns:
        All outputs for the step.

    Raises:
        401 error: when not authorized to login
        404 error: when trigger does not exist
        422 error: when unable to validate input
    """
    try:
        return zen_store.get_run_step_outputs(step_id)
    except NotAuthorizedError as error:
        raise HTTPException(status_code=401, detail=error_detail(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=error_detail(error))
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error_detail(error))
