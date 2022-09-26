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
"""Zen Server API."""
import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware

import zenml
from zenml.zen_server.routers import (
    artifacts_endpoints,
    auth_endpoints,
    flavors_endpoints,
    metadata_config_endpoints,
    pipelines_endpoints,
    projects_endpoints,
    roles_endpoints,
    runs_endpoints,
    stack_components_endpoints,
    stacks_endpoints,
    steps_endpoints,
    teams_endpoints,
    users_endpoints,
)
from zenml.zen_server.utils import ROOT_URL_PATH

DASHBOARD_DIRECTORY = "dashboard"


def relative_path(rel: str) -> str:
    """Get the absolute path of a path relative to the ZenML server module.

    Args:
        rel: Relative path.

    Returns:
        Absolute path.
    """
    return os.path.join(os.path.dirname(__file__), rel)


app = FastAPI(
    title="ZenML",
    version=zenml.__version__,
    root_path=ROOT_URL_PATH,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_headers=["*"],
)

app.mount(
    "/dashboard/static",
    StaticFiles(
        directory=relative_path(os.path.join(DASHBOARD_DIRECTORY, "static")),
        check_dir=False,
    ),
)

templates = Jinja2Templates(directory=relative_path(DASHBOARD_DIRECTORY))


@app.get("/")
def dashboard(request: Request) -> Any:
    """Dashboard endpoint.

    Args:
        request: Request object.

    Returns:
        The ZenML dashboard.
    """
    return templates.TemplateResponse("index.html", {"request": request})


# Basic Health Endpoint
@app.head("/health", include_in_schema=False)
@app.get("/health")
def health() -> str:
    """Get health status of the server.

    Returns:
        String representing the health status of the server.
    """
    return "OK"


@app.get("/version")
def version() -> str:
    """Get version of the server.

    Returns:
        String representing the version of the server.
    """
    return zenml.__version__


# to run this file locally, execute:
# uvicorn zenml.zen_server.zen_server_api:app --reload


app.include_router(auth_endpoints.router)
app.include_router(metadata_config_endpoints.router)
app.include_router(pipelines_endpoints.router)
app.include_router(projects_endpoints.router)
app.include_router(flavors_endpoints.router)
app.include_router(roles_endpoints.router)
app.include_router(runs_endpoints.router)
app.include_router(stacks_endpoints.router)
app.include_router(stack_components_endpoints.router)
app.include_router(stack_components_endpoints.types_router)
app.include_router(steps_endpoints.router)
app.include_router(artifacts_endpoints.router)
app.include_router(teams_endpoints.router)
app.include_router(users_endpoints.router)
app.include_router(users_endpoints.current_user_router)
app.include_router(users_endpoints.activation_router)
