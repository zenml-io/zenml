# #  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
# #
# #  Licensed under the Apache License, Version 2.0 (the "License");
# #  you may not use this file except in compliance with the License.
# #  You may obtain a copy of the License at:
# #
# #       https://www.apache.org/licenses/LICENSE-2.0
# #
# #  Unless required by applicable law or agreed to in writing, software
# #  distributed under the License is distributed on an "AS IS" BASIS,
# #  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# #  or implied. See the License for the specific language governing
# #  permissions and limitations under the License.
# from typing import Dict, List

# from fastapi import APIRouter, Depends, HTTPException

# from zenml.constants import DEFAULT_STACK, RUNTIME_CONFIGURATION, TRIGGERS
# from zenml.zen_server.zen_server_api import (
#     authorize,
#     error_detail,
#     error_response,
#     zen_store,
# )

# router = APIRouter(
#     prefix=TRIGGERS,
#     tags=["triggers"],
#     dependencies=[Depends(authorize)],
#     responses={401: error_response},
# )


# @router.get(
#     "/{trigger_id}",
#     response_model=Dict,
#     responses={401: error_response, 404: error_response, 422: error_response},
# )
# async def get_pipeline(trigger_id: str) -> Dict:
#     """Gets a specific trigger using its unique id.

#     Args:
#         trigger_id: ID of the pipeline to get.

#     Returns:
#         A specific trigger object.

#     Raises:
#         401 error: when not authorized to login
#         404 error: when trigger does not exist
#         422 error: when unable to validate input
#     """
#     try:
#         return zen_store.get_trigger(trigger_id)
#     except NotAuthorizedError as error:
#         raise HTTPException(status_code=401, detail=error_detail(error))
#     except NotFoundError as error:
#         raise HTTPException(status_code=404, detail=error_detail(error))
#     except ValidationError as error:
#         raise HTTPException(status_code=422, detail=error_detail(error))


# @router.put(
#     "/{trigger_id}",
#     response_model=Dict,
#     responses={401: error_response, 404: error_response, 422: error_response},
# )
# async def update_trigger(trigger_id: str, trigger) -> Dict:
#     """Updates an attribute on a specific trigger using its unique id.

#     For a schedule this might be the schedule interval.

#     Args:
#         trigger_id: ID of the pipeline to get.
#         trigger: the trigger object to use to update.

#     Returns:
#         The updated trigger.

#     Raises:
#         401 error: when not authorized to login
#         404 error: when trigger does not exist
#         422 error: when unable to validate input
#     """
#     try:
#         return zen_store.update_trigger(trigger_id, trigger)
#     except NotAuthorizedError as error:
#         raise HTTPException(status_code=401, detail=error_detail(error))
#     except NotFoundError as error:
#         raise HTTPException(status_code=404, detail=error_detail(error))
#     except ValidationError as error:
#         raise HTTPException(status_code=422, detail=error_detail(error))


# @router.delete(
#     "/{trigger_id}",
#     responses={401: error_response, 404: error_response, 422: error_response},
# )
# async def delete_trigger(trigger_id: str) -> None:
#     """Delete a specific pipeline trigger.

#     Runs that are in progress are not canceled by this.

#     Args:
#         trigger_id: ID of the pipeline to get.

#     Raises:
#         401 error: when not authorized to login
#         404 error: when trigger does not exist
#         422 error: when unable to validate input
#     """
#     try:
#         zen_store.delete_trigger(trigger_id)
#     except NotAuthorizedError as error:
#         raise HTTPException(status_code=401, detail=error_detail(error))
#     except NotFoundError as error:
#         raise HTTPException(status_code=404, detail=error_detail(error))
#     except ValidationError as error:
#         raise HTTPException(status_code=422, detail=error_detail(error))


# @router.get(
#     "/{trigger_id}" + DEFAULT_STACK,
#     response_model=List[Dict],
#     responses={401: error_response, 404: error_response, 422: error_response},
# )
# async def get_trigger_default_stack(trigger_id: str) -> List[Dict]:
#     """Get the default stack used by a specific trigger.

#     Args:
#         trigger_id: ID of the pipeline to get.

#     Returns:
#         The stack used by a specific trigger.

#     Raises:
#         401 error: when not authorized to login
#         404 error: when trigger does not exist
#         422 error: when unable to validate input
#     """
#     try:
#         return zen_store.get_trigger_default_stack(trigger_id)
#     except NotAuthorizedError as error:
#         raise HTTPException(status_code=401, detail=error_detail(error))
#     except NotFoundError as error:
#         raise HTTPException(status_code=404, detail=error_detail(error))
#     except ValidationError as error:
#         raise HTTPException(status_code=422, detail=error_detail(error))


# @router.put(
#     "/{trigger_id}" + DEFAULT_STACK + "/{stack_id}",
#     response_model=List[Dict],
#     responses={401: error_response, 404: error_response, 422: error_response},
# )
# async def update_trigger_default_stack(
#     trigger_id: str, stack_id: str
# ) -> List[Dict]:
#     """Update the default stack used by a specific trigger.

#     Args:
#         trigger_id: ID of the pipeline to update.
#         stack_id: ID of the stack to use.

#     Returns:
#         The updated default stack.

#     Raises:
#         401 error: when not authorized to login
#         404 error: when trigger does not exist
#         422 error: when unable to validate input
#     """
#     try:
#         return zen_store.update_trigger_default_stack(trigger_id, stack_id)
#     except NotAuthorizedError as error:
#         raise HTTPException(status_code=401, detail=error_detail(error))
#     except NotFoundError as error:
#         raise HTTPException(status_code=404, detail=error_detail(error))
#     except ValidationError as error:
#         raise HTTPException(status_code=422, detail=error_detail(error))


# @router.put(
#     "/{trigger_id}" + RUNTIME_CONFIGURATION,
#     response_model=Dict,
#     responses={401: error_response, 404: error_response, 422: error_response},
# )
# async def update_trigger_default_stack(
#     trigger_id: str, runtime_configuration
# ) -> Dict:
#     """Updates the pipeline runtime configuration used for triggered runs.

#     Args:
#         trigger_id: ID of the pipeline to update.

#     Returns:
#         The updated pipeline runtime configuration. # TODO: is this correct?

#     Raises:
#         401 error: when not authorized to login
#         404 error: when trigger does not exist
#         422 error: when unable to validate input
#     """
#     try:
#         return zen_store.update_trigger_runtime_configuration(
#             trigger_id, runtime_configuration
#         )
#     except NotAuthorizedError as error:
#         raise HTTPException(status_code=401, detail=error_detail(error))
#     except NotFoundError as error:
#         raise HTTPException(status_code=404, detail=error_detail(error))
#     except ValidationError as error:
#         raise HTTPException(status_code=422, detail=error_detail(error))
