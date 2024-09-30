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
"""Zen Server API.

To run this file locally, execute:

    ```
    uvicorn zenml.zen_server.zen_server_api:app --reload
    ```
"""

import os
from asyncio.log import logger
from datetime import datetime, timedelta, timezone
from genericpath import isfile
from typing import Any, List, Set

from anyio import to_thread
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.types import ASGIApp

import zenml
from zenml.analytics import source_context
from zenml.constants import (
    API,
    DEFAULT_ZENML_SERVER_REPORT_USER_ACTIVITY_TO_DB_SECONDS,
    HEALTH,
)
from zenml.enums import AuthScheme, SourceContextTypes
from zenml.zen_server.exceptions import error_detail
from zenml.zen_server.routers import (
    actions_endpoints,
    artifact_endpoint,
    artifact_version_endpoints,
    auth_endpoints,
    code_repositories_endpoints,
    devices_endpoints,
    event_source_endpoints,
    flavors_endpoints,
    model_versions_endpoints,
    models_endpoints,
    pipeline_builds_endpoints,
    pipeline_deployments_endpoints,
    pipelines_endpoints,
    plugin_endpoints,
    run_metadata_endpoints,
    run_templates_endpoints,
    runs_endpoints,
    schedule_endpoints,
    secrets_endpoints,
    server_endpoints,
    service_accounts_endpoints,
    service_connectors_endpoints,
    service_endpoints,
    stack_components_endpoints,
    stack_deployment_endpoints,
    stacks_endpoints,
    steps_endpoints,
    tags_endpoints,
    triggers_endpoints,
    users_endpoints,
    webhook_endpoints,
    workspaces_endpoints,
)
from zenml.zen_server.secure_headers import (
    initialize_secure_headers,
    secure_headers,
)
from zenml.zen_server.utils import (
    initialize_feature_gate,
    initialize_plugins,
    initialize_rbac,
    initialize_workload_manager,
    initialize_zen_store,
    is_user_request,
    server_config,
    zen_store,
)

if server_config().use_legacy_dashboard:
    DASHBOARD_DIRECTORY = "dashboard_legacy"
else:
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

# Initialize last_user_activity
last_user_activity: datetime = datetime.now(timezone.utc)
last_user_activity_reported: datetime = datetime.now(timezone.utc) + timedelta(
    seconds=-DEFAULT_ZENML_SERVER_REPORT_USER_ACTIVITY_TO_DB_SECONDS
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


class RequestBodyLimit(BaseHTTPMiddleware):
    """Limits the size of the request body."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        """Limits the size of the request body.

        Args:
            app: The FastAPI app.
            max_bytes: The maximum size of the request body.
        """
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Limits the size of the request body.

        Args:
            request: The incoming request.
            call_next: The next function to be called.

        Returns:
            The response to the request.
        """
        if content_length := request.headers.get("content-length"):
            if int(content_length) > self.max_bytes:
                return Response(status_code=413)  # Request Entity Too Large
        return await call_next(request)


class RestrictFileUploadsMiddleware(BaseHTTPMiddleware):
    """Restrict file uploads to certain paths."""

    def __init__(self, app: FastAPI, allowed_paths: Set[str]):
        """Restrict file uploads to certain paths.

        Args:
            app: The FastAPI app.
            allowed_paths: The allowed paths.
        """
        super().__init__(app)
        self.allowed_paths = allowed_paths

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Restrict file uploads to certain paths.

        Args:
            request: The incoming request.
            call_next: The next function to be called.

        Returns:
            The response to the request.
        """
        if request.method == "POST":
            content_type = request.headers.get("content-type", "")
            if (
                "multipart/form-data" in content_type
                and request.url.path not in self.allowed_paths
            ):
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "File uploads are not allowed on this endpoint."
                    },
                )
        return await call_next(request)


ALLOWED_FOR_FILE_UPLOAD: Set[str] = set()

app.add_middleware(
    CORSMiddleware,
    allow_origins=server_config().cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    RequestBodyLimit, max_bytes=server_config().max_request_body_size_in_bytes
)
app.add_middleware(
    RestrictFileUploadsMiddleware, allowed_paths=ALLOWED_FOR_FILE_UPLOAD
)


@app.middleware("http")
async def set_secure_headers(request: Request, call_next: Any) -> Any:
    """Middleware to set secure headers.

    Args:
        request: The incoming request.
        call_next: The next function to be called.

    Returns:
        The response with secure headers set.
    """
    # If the request is for the openAPI docs, don't set secure headers
    if request.url.path.startswith("/docs") or request.url.path.startswith(
        "/redoc"
    ):
        return await call_next(request)

    response = await call_next(request)
    secure_headers().framework.fastapi(response)
    return response


@app.middleware("http")
async def track_last_user_activity(request: Request, call_next: Any) -> Any:
    """A middleware to track last user activity.

    This middleware checks if the incoming request is a user request and
    updates the last activity timestamp if it is.

    Args:
        request: The incoming request object.
        call_next: A function that will receive the request as a parameter and
            pass it to the corresponding path operation.

    Returns:
        The response to the request.
    """
    global last_user_activity
    global last_user_activity_reported

    try:
        if is_user_request(request):
            last_user_activity = datetime.now(timezone.utc)
    except Exception as e:
        logger.debug(
            f"An unexpected error occurred while checking user activity: {e}"
        )
    if (
        (
            datetime.now(timezone.utc) - last_user_activity_reported
        ).total_seconds()
        > DEFAULT_ZENML_SERVER_REPORT_USER_ACTIVITY_TO_DB_SECONDS
    ):
        last_user_activity_reported = datetime.now(timezone.utc)
        zen_store()._update_last_user_activity_timestamp(
            last_user_activity=last_user_activity
        )
    return await call_next(request)


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
    # Set the maximum number of worker threads
    to_thread.current_default_thread_limiter().total_tokens = (
        server_config().thread_pool_size
    )
    # IMPORTANT: these need to be run before the fastapi app starts, to avoid
    # race conditions
    initialize_zen_store()
    initialize_rbac()
    initialize_feature_gate()
    initialize_workload_manager()
    initialize_plugins()
    initialize_secure_headers()


if server_config().use_legacy_dashboard:
    app.mount(
        "/static",
        StaticFiles(
            directory=relative_path(
                os.path.join(DASHBOARD_DIRECTORY, "static")
            ),
            check_dir=False,
        ),
    )
else:
    app.mount(
        "/assets",
        StaticFiles(
            directory=relative_path(
                os.path.join(DASHBOARD_DIRECTORY, "assets")
            ),
            check_dir=False,
        ),
    )


# Basic Health Endpoint
@app.head(HEALTH, include_in_schema=False)
@app.get(HEALTH)
async def health() -> str:
    """Get health status of the server.

    Returns:
        String representing the health status of the server.
    """
    return "OK"


templates = Jinja2Templates(directory=relative_path(DASHBOARD_DIRECTORY))


@app.get("/", include_in_schema=False)
async def dashboard(request: Request) -> Any:
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


app.include_router(actions_endpoints.router)
app.include_router(artifact_endpoint.artifact_router)
app.include_router(artifact_version_endpoints.artifact_version_router)
app.include_router(auth_endpoints.router)
app.include_router(devices_endpoints.router)
app.include_router(code_repositories_endpoints.router)
app.include_router(plugin_endpoints.plugin_router)
app.include_router(event_source_endpoints.event_source_router)
app.include_router(flavors_endpoints.router)
app.include_router(models_endpoints.router)
app.include_router(model_versions_endpoints.router)
app.include_router(model_versions_endpoints.model_version_artifacts_router)
app.include_router(model_versions_endpoints.model_version_pipeline_runs_router)
app.include_router(pipelines_endpoints.router)
app.include_router(pipeline_builds_endpoints.router)
app.include_router(pipeline_deployments_endpoints.router)
app.include_router(runs_endpoints.router)
app.include_router(run_metadata_endpoints.router)
app.include_router(run_templates_endpoints.router)
app.include_router(schedule_endpoints.router)
app.include_router(secrets_endpoints.router)
app.include_router(secrets_endpoints.op_router)
app.include_router(server_endpoints.router)
app.include_router(service_accounts_endpoints.router)
app.include_router(service_connectors_endpoints.router)
app.include_router(service_connectors_endpoints.types_router)
app.include_router(service_endpoints.router)
app.include_router(stack_deployment_endpoints.router)
app.include_router(stacks_endpoints.router)
app.include_router(stack_components_endpoints.router)
app.include_router(stack_components_endpoints.types_router)
app.include_router(steps_endpoints.router)
app.include_router(tags_endpoints.router)
app.include_router(triggers_endpoints.router)
app.include_router(users_endpoints.router)
app.include_router(users_endpoints.current_user_router)
app.include_router(webhook_endpoints.router)
app.include_router(workspaces_endpoints.router)

# When the auth scheme is set to EXTERNAL, users cannot be managed via the
# API.
if server_config().auth_scheme != AuthScheme.EXTERNAL:
    app.include_router(users_endpoints.activation_router)


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
async def invalid_api(invalid_api_path: str) -> None:
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
async def catch_all(request: Request, file_path: str) -> Any:
    """Dashboard endpoint.

    Args:
        request: Request object.
        file_path: Path to a file in the dashboard root folder.

    Returns:
        The ZenML dashboard.
    """
    # some static files need to be served directly from the root dashboard
    # directory
    if file_path and file_path in root_static_files:
        logger.debug(f"Returning static file: {file_path}")
        full_path = os.path.join(relative_path(DASHBOARD_DIRECTORY), file_path)
        return FileResponse(full_path)

    # everything else is directed to the index.html file that hosts the
    # single-page application
    return templates.TemplateResponse("index.html", {"request": request})
