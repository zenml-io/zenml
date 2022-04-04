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
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI

from zenml.enums import StackComponentType
from zenml.io.utils import get_global_config_directory
from zenml.stack_stores import BaseStackStore, SqlStackStore
from zenml.stack_stores.models import (
    StackComponentWrapper,
    StackWrapper,
    Version,
)

app = FastAPI()

# to run this, execute:
# uvicorn zenml.zen_service.zen_service:app --reload


root: Path = Path(get_global_config_directory())
url = f"sqlite:///{root / 'service_stack_store.db'}"
print(url)
stack_store: BaseStackStore = SqlStackStore().initialize(url)


@app.head("/health")
async def health() -> str:
    return "OK"


@app.get(
    "/stacks/configurations/{name}",
    response_model=Dict[StackComponentType, str],
)
async def get_stack_configuration(name: str) -> Dict[StackComponentType, str]:
    return stack_store.get_stack_configuration(name)


@app.get(
    "/stacks/configurations/",
    response_model=Dict[str, Dict[StackComponentType, str]],
)
async def stack_configurations() -> Dict[str, Dict[StackComponentType, str]]:
    return stack_store.stack_configurations


@app.post("/components/register")
async def register_stack_component(
    component: StackComponentWrapper,
) -> None:
    stack_store.register_stack_component(component)


@app.get("/stacks", response_model=List[StackWrapper])
async def stacks() -> List[StackWrapper]:
    return [
        StackWrapper(name=s.name, components=s.components)
        for s in stack_store.stacks
    ]


@app.post("/stacks/register", response_model=Dict[str, str])
def register_stack(stack: StackWrapper) -> Dict[str, str]:
    return stack_store.register_stack(stack)


@app.get("/stacks/{name}", response_model=StackWrapper)
async def get_stack(name: str) -> StackWrapper:
    return stack_store.get_stack(name)


@app.get("stacks/{name}/deregister")
def deregister_stack(name: str) -> None:
    stack_store.deregister_stack(name)


@app.get(
    "/components/{component_type}/{name}",
    response_model=StackComponentWrapper,
)
async def get_stack_component(
    component_type: StackComponentType, name: str
) -> StackComponentWrapper:
    return stack_store.get_stack_component(component_type, name=name)


@app.get(
    "/components/{component_type}",
    response_model=List[StackComponentWrapper],
)
def get_stack_components(
    component_type: StackComponentType,
) -> List[StackComponentWrapper]:
    return stack_store.get_stack_components(component_type)


@app.get("/components/deregister/{component_type}/{name}")
async def deregister_stack_component(
    component_type: StackComponentType, name: str
) -> None:
    return stack_store.deregister_stack_component(component_type, name=name)
