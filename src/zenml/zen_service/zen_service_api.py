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
import os
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from zenml.config.global_config import GlobalConfiguration
from zenml.config.profile_config import ProfileConfiguration
from zenml.constants import (
    ENV_ZENML_PROFILE_NAME,
    IS_EMPTY,
    STACK_COMPONENTS,
    STACK_CONFIGURATIONS,
    STACKS,
)
from zenml.enums import StackComponentType, StoreType
from zenml.exceptions import StackComponentExistsError, StackExistsError
from zenml.repository import Repository
from zenml.stack_stores import BaseStackStore
from zenml.stack_stores.models import StackComponentWrapper, StackWrapper

profile_configuration_json = os.environ.get("ZENML_PROFILE_CONFIGURATION")
profile_name = os.environ.get(ENV_ZENML_PROFILE_NAME)

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


if profile.store_type == StoreType.REST:
    raise ValueError(
        "Service cannot be started with REST store type. Make sure you "
        "specify a profile with a non-networked persistence backend "
        "when trying to start the Zen Service. (use command line flag "
        "`--profile=$PROFILE_NAME` or set the env variable "
        f"{ENV_ZENML_PROFILE_NAME} to specify the use of a profile "
        "other than the currently active one)"
    )
stack_store: BaseStackStore = Repository.create_store(profile)

app = FastAPI(title="ZenML", version="0.7.0")

# to run this file locally, execute:
# uvicorn zenml.zen_service.zen_service_api:app --reload


class ErrorModel(BaseModel):
    detail: Any


error_response = dict(model=ErrorModel)


def error_detail(error: Exception) -> List[str]:
    """Convert an Exception to API representation."""
    return [type(error).__name__] + [str(a) for a in error.args]


def not_found(error: Exception) -> HTTPException:
    """Convert an Exception to a HTTP 404 response."""
    return HTTPException(status_code=404, detail=error_detail(error))


def conflict(error: Exception) -> HTTPException:
    """Convert an Exception to a HTTP 404 response."""
    return HTTPException(status_code=409, detail=error_detail(error))


@app.get("/", response_model=ProfileConfiguration)
async def service_info() -> ProfileConfiguration:
    return profile


@app.head("/health")
@app.get("/health")
async def health() -> str:
    return "OK"


@app.get(IS_EMPTY, response_model=bool)
async def is_empty() -> bool:
    return stack_store.is_empty


@app.get(
    STACK_CONFIGURATIONS + "/{name}",
    response_model=Dict[StackComponentType, str],
    responses={404: error_response},
)
async def get_stack_configuration(name: str) -> Dict[StackComponentType, str]:
    try:
        return stack_store.get_stack_configuration(name)
    except KeyError as error:
        raise not_found(error) from error


@app.get(
    STACK_CONFIGURATIONS,
    response_model=Dict[str, Dict[StackComponentType, str]],
)
async def stack_configurations() -> Dict[str, Dict[StackComponentType, str]]:
    return stack_store.stack_configurations


@app.post(STACK_COMPONENTS, responses={409: error_response})
async def register_stack_component(
    component: StackComponentWrapper,
) -> None:
    try:
        stack_store.register_stack_component(component)
    except StackComponentExistsError as error:
        raise conflict(error) from error


@app.delete(STACKS + "/{name}", responses={404: error_response})
async def deregister_stack(name: str) -> None:
    try:
        stack_store.deregister_stack(name)
    except KeyError as error:
        raise not_found(error) from error


@app.get(STACKS, response_model=List[StackWrapper])
async def stacks() -> List[StackWrapper]:
    return stack_store.stacks


@app.get(
    STACKS + "/{name}",
    response_model=StackWrapper,
    responses={404: error_response},
)
async def get_stack(name: str) -> StackWrapper:
    try:
        return stack_store.get_stack(name)
    except KeyError as error:
        raise not_found(error) from error


@app.post(
    STACKS,
    response_model=Dict[str, str],
    responses={409: error_response},
)
async def register_stack(stack: StackWrapper) -> Dict[str, str]:
    try:
        return stack_store.register_stack(stack)
    except (StackExistsError, StackComponentExistsError) as error:
        raise conflict(error) from error


@app.get(
    STACK_COMPONENTS + "/{component_type}/{name}",
    response_model=StackComponentWrapper,
    responses={404: error_response},
)
async def get_stack_component(
    component_type: StackComponentType, name: str
) -> StackComponentWrapper:
    try:
        return stack_store.get_stack_component(component_type, name=name)
    except KeyError as error:
        raise not_found(error) from error


@app.get(
    STACK_COMPONENTS + "/{component_type}",
    response_model=List[StackComponentWrapper],
)
async def get_stack_components(
    component_type: StackComponentType,
) -> List[StackComponentWrapper]:
    return stack_store.get_stack_components(component_type)


@app.delete(
    STACK_COMPONENTS + "/{component_type}/{name}",
    responses={404: error_response, 409: error_response},
)
async def deregister_stack_component(
    component_type: StackComponentType, name: str
) -> None:
    try:
        return stack_store.deregister_stack_component(component_type, name=name)
    except KeyError as error:
        raise not_found(error) from error
    except ValueError as error:
        raise conflict(error) from error
