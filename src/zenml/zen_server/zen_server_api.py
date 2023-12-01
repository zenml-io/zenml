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
from asyncio.log import logger
from typing import Any, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from genericpath import isfile
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse

import zenml
from zenml.analytics import source_context
from zenml.constants import API, HEALTH
from zenml.enums import AuthScheme, SourceContextTypes
from zenml.zen_server.exceptions import error_detail
from zenml.zen_server.routers import (
    artifact_endpoint,
    artifact_version_endpoints,
    auth_endpoints,
    code_repositories_endpoints,
    devices_endpoints,
    flavors_endpoints,
    model_versions_endpoints,
    models_endpoints,
    pipeline_builds_endpoints,
    pipeline_deployments_endpoints,
    pipelines_endpoints,
    run_metadata_endpoints,
    runs_endpoints,
    schedule_endpoints,
    secrets_endpoints,
    server_endpoints,
    service_accounts_endpoints,
    service_connectors_endpoints,
    stack_components_endpoints,
    stacks_endpoints,
    steps_endpoints,
    tags_endpoints,
    users_endpoints,
    workspaces_endpoints,
)
from zenml.zen_server.utils import (
    initialize_rbac,
    initialize_zen_store,
    server_config,
)

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
    root_path=server_config().root_url_path,
    default_response_class=ORJSONResponse,
)


# Customize the default request validation handler that comes with FastAPI
# to return a JSON response that matches the ZenML API spec.
@app.exception_handler(RequestValidationError)
def validation_exception_handler(
    request: Any, exc: Exception
) -> ORJSONResponse:
    """Custom validation exception handler.

    Args:
        request: The request.
        exc: The exception.

    Returns:
        The error response formatted using the ZenML API conventions.
    """
    return ORJSONResponse(error_detail(exc, ValueError), status_code=422)


app.add_middleware(
    CORSMiddleware,
    allow_origins=server_config().cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def infer_source_context(request: Request, call_next: Any) -> Any:
    """A middleware to track the source of an event.

    It extracts the source context from the header of incoming requests
    and applies it to the ZenML source context on the API side. This way, the
    outgoing analytics request can append it as an additional field.

    Args:
        request: the incoming request object.
        call_next: a function that will receive the request as a parameter and
            pass it to the corresponding path operation.

    Returns:
        the response to the request.
    """
    try:
        s = request.headers.get(
            source_context.name,
            default=SourceContextTypes.API.value,
        )
        source_context.set(SourceContextTypes(s))
    except Exception as e:
        logger.warning(
            f"An unexpected error occurred while getting the source "
            f"context: {e}"
        )
        source_context.set(SourceContextTypes.API)

    return await call_next(request)


@app.on_event("startup")
def initialize() -> None:
    """Initialize the ZenML server."""
    # IMPORTANT: these need to be run before the fastapi app starts, to avoid
    # race conditions
    initialize_zen_store()
    initialize_rbac()


app.mount(
    "/static",
    StaticFiles(
        directory=relative_path(os.path.join(DASHBOARD_DIRECTORY, "static")),
        check_dir=False,
    ),
)


# Basic Health Endpoint
@app.head(HEALTH, include_in_schema=False)
@app.get(HEALTH)
def health() -> str:
    """Get health status of the server.

    Returns:
        String representing the health status of the server.
    """
    return "OK"


templates = Jinja2Templates(directory=relative_path(DASHBOARD_DIRECTORY))


@app.get("/", include_in_schema=False)
def dashboard(request: Request) -> Any:
    """Dashboard endpoint.

    Args:
        request: Request object.

    Returns:
        The ZenML dashboard.

    Raises:
        HTTPException: If the dashboard files are not included.
    """
    if not os.path.isfile(
        os.path.join(relative_path(DASHBOARD_DIRECTORY), "index.html")
    ):
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("index.html", {"request": request})


# to run this file locally, execute:
# uvicorn zenml.zen_server.zen_server_api:app --reload


app.include_router(auth_endpoints.router)
app.include_router(devices_endpoints.router)
app.include_router(pipelines_endpoints.router)
app.include_router(workspaces_endpoints.router)
app.include_router(flavors_endpoints.router)
app.include_router(runs_endpoints.router)
app.include_router(run_metadata_endpoints.router)
app.include_router(schedule_endpoints.router)
app.include_router(secrets_endpoints.router)
app.include_router(server_endpoints.router)
app.include_router(service_accounts_endpoints.router)
app.include_router(service_connectors_endpoints.router)
app.include_router(service_connectors_endpoints.types_router)
app.include_router(stacks_endpoints.router)
app.include_router(stack_components_endpoints.router)
app.include_router(stack_components_endpoints.types_router)
app.include_router(steps_endpoints.router)
app.include_router(artifact_endpoint.artifact_router)
app.include_router(artifact_version_endpoints.artifact_version_router)
app.include_router(users_endpoints.router)
app.include_router(users_endpoints.current_user_router)

# When the auth scheme is set to EXTERNAL, users cannot be managed via the
# API.
if server_config().auth_scheme != AuthScheme.EXTERNAL:
    app.include_router(users_endpoints.activation_router)

app.include_router(pipeline_builds_endpoints.router)
app.include_router(pipeline_deployments_endpoints.router)
app.include_router(code_repositories_endpoints.router)
app.include_router(models_endpoints.router)
app.include_router(model_versions_endpoints.router)
app.include_router(model_versions_endpoints.model_version_artifacts_router)
app.include_router(model_versions_endpoints.model_version_pipeline_runs_router)
app.include_router(tags_endpoints.router)


def get_root_static_files() -> List[str]:
    """Get the list of static files in the root dashboard directory.

    These files are static files that are not in the /static subdirectory
    that need to be served as static files under the root URL path.

    Returns:
        List of static files in the root directory.
    """
    root_path = relative_path(DASHBOARD_DIRECTORY)
    if not os.path.isdir(root_path):
        return []
    files = []
    for file in os.listdir(root_path):
        if file == "index.html":
            # this is served separately
            continue
        if isfile(os.path.join(root_path, file)):
            files.append(file)
    return files


# save these globally to avoid having to poll the filesystem on every request
root_static_files = get_root_static_files()


@app.get(
    API + "/{invalid_api_path:path}", status_code=404, include_in_schema=False
)
def invalid_api(invalid_api_path: str) -> None:
    """Invalid API endpoint.

    All API endpoints that are not defined in the API routers will be
    redirected to this endpoint and will return a 404 error.

    Args:
        invalid_api_path: Invalid API path.

    Raises:
        HTTPException: 404 error.
    """
    logger.debug(f"Invalid API path requested: {invalid_api_path}")
    raise HTTPException(status_code=404)


@app.get("/{file_path:path}", include_in_schema=False)
def catch_all(request: Request, file_path: str) -> Any:
    """Dashboard endpoint.

    Args:
        request: Request object.
        file_path: Path to a file in the dashboard root folder.

    Returns:
        The ZenML dashboard.

    Raises:
        HTTPException: 404 error if requested a non-existent static file or if
            the dashboard files are not included.
    """
    # some static files need to be served directly from the root dashboard
    # directory
    if file_path and file_path in root_static_files:
        logger.debug(f"Returning static file: {file_path}")
        full_path = os.path.join(relative_path(DASHBOARD_DIRECTORY), file_path)
        return FileResponse(full_path)

    tokens = file_path.split("/")
    if len(tokens) == 1 and not request.query_params:
        logger.debug(f"Requested non-existent static file: {file_path}")
        raise HTTPException(status_code=404)

    if not os.path.isfile(
        os.path.join(relative_path(DASHBOARD_DIRECTORY), "index.html")
    ):
        raise HTTPException(status_code=404)

    # everything else is directed to the index.html file that hosts the
    # single-page application
    return templates.TemplateResponse("index.html", {"request": request})
