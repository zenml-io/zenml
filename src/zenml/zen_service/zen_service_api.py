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
import logging
import os
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from zenml.config.global_config import GlobalConfiguration
from zenml.config.profile_config import ProfileConfiguration
from zenml.enums import StackComponentType
from zenml.exceptions import StackComponentExistsError, StackExistsError
from zenml.repository import Repository
from zenml.stack_stores import BaseStackStore
from zenml.stack_stores.models import StackComponentWrapper, StackWrapper

# """
profile_configuration_json = os.environ.get("ZENML_PROFILE_CONFIGURATION")
profile_name = os.environ.get("ZENML_PROFILE_NAME")

# Hopefully profile configuration was passed as env variable:
if profile_configuration_json:
    profile = ProfileConfiguration.parse_raw(profile_configuration_json)
# Otherwise check if profile name was passed as env variable:
elif profile_name:
    profile = (
        GlobalConfiguration().get_profile(profile_name)
        or Repository().active_profile
    )
# Fallback to what Repository thinks is the active profile
else:
    profile = Repository().active_profile


stack_store: BaseStackStore = Repository.create_store(
    profile, skip_default_stack=True
)

app = FastAPI()

# to run this, execute:
# uvicorn zenml.zen_service.zen_service:app --reload


class ErrorModel(BaseModel):
    detail: Any


error_response = dict(model=ErrorModel)


@app.get("/", response_model=ProfileConfiguration)
async def service_info() -> ProfileConfiguration:
    return profile


@app.head("/health")
@app.get("/health")
async def health() -> str:
    return "OK"


@app.get(
    "/stacks/get-configurations/{name}",
    response_model=Dict[StackComponentType, str],
    responses={404: error_response},
)
async def get_stack_configuration(name: str) -> Dict[StackComponentType, str]:
    try:
        return stack_store.get_stack_configuration(name)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=error.args
        ) from error


@app.get(
    "/stacks/get-configurations",
    response_model=Dict[str, Dict[StackComponentType, str]],
)
async def stack_configurations() -> Dict[str, Dict[StackComponentType, str]]:
    return stack_store.stack_configurations


@app.post("/components/register", responses={409: error_response})
async def register_stack_component(
    component: StackComponentWrapper,
) -> None:
    try:
        stack_store.register_stack_component(component)
    except StackComponentExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=error.args
        ) from error


@app.get("/stacks/delete/{name}")
async def deregister_stack(name: str) -> None:
    logging.warning(f"About to delete stack {name}")
    try:
        stack_store.deregister_stack(name)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=error.args
        ) from error


@app.get("/stacks/get", response_model=List[StackWrapper])
async def stacks() -> List[StackWrapper]:
    return stack_store.stacks


@app.get(
    "/stacks/get/{name}",
    response_model=StackWrapper,
    responses={404: error_response},
)
async def get_stack(name: str) -> StackWrapper:
    try:
        return stack_store.get_stack(name)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=error.args
        ) from error


@app.post(
    "/stacks/register",
    response_model=Dict[str, str],
    responses={404: error_response, 409: error_response},
)
async def register_stack(stack: StackWrapper) -> Dict[str, str]:
    try:
        return stack_store.register_stack(stack)
    except StackComponentExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=error.args
        ) from error
    except StackExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=error.args
        ) from error


@app.get(
    "/components/get/{component_type}/{name}",
    response_model=StackComponentWrapper,
)
async def get_stack_component(
    component_type: StackComponentType, name: str
) -> StackComponentWrapper:
    return stack_store.get_stack_component(component_type, name=name)


@app.get(
    "/components/get/{component_type}",
    response_model=List[StackComponentWrapper],
)
async def get_stack_components(
    component_type: StackComponentType,
) -> List[StackComponentWrapper]:
    return stack_store.get_stack_components(component_type)


@app.get("/components/delete/{component_type}/{name}")
async def deregister_stack_component(
    component_type: StackComponentType, name: str
) -> None:
    try:
        return stack_store.deregister_stack_component(component_type, name=name)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=error.args
        ) from error
