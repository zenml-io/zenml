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
"""Server middlewares."""

import logging
from asyncio import Lock
from asyncio.log import logger
from datetime import datetime, timedelta
from typing import Any, Set

from anyio import CapacityLimiter, to_thread
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import (
    JSONResponse,
    Response,
)
from starlette.types import ASGIApp

from zenml.analytics import source_context
from zenml.constants import (
    DEFAULT_ZENML_SERVER_REPORT_USER_ACTIVITY_TO_DB_SECONDS,
    HEALTH,
    READY,
)
from zenml.enums import SourceContextTypes
from zenml.utils.time_utils import utc_now
from zenml.zen_server.request_management import RequestContext
from zenml.zen_server.secure_headers import (
    secure_headers,
)
from zenml.zen_server.utils import (
    get_system_metrics_log_str,
    is_user_request,
    request_manager,
    server_config,
    zen_store,
)

# Track active requests with an atomic counter
active_requests_count = 0
active_requests_lock = Lock()


# Initialize last_user_activity
last_user_activity: datetime = utc_now()
last_user_activity_reported: datetime = last_user_activity + timedelta(
    seconds=-DEFAULT_ZENML_SERVER_REPORT_USER_ACTIVITY_TO_DB_SECONDS
)
last_user_activity_lock = Lock()
# Create a custom thread pool limiter with a limit of 1 thread for all
# user activity updates
last_user_activity_thread_limiter = CapacityLimiter(1)


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

        try:
            return await call_next(request)
        except Exception:
            logger.exception("An error occurred while processing the request")
            return JSONResponse(
                status_code=500,
                content={"detail": "An unexpected error occurred."},
            )


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

        try:
            return await call_next(request)
        except Exception:
            logger.exception("An error occurred while processing the request")
            return JSONResponse(
                status_code=500,
                content={"detail": "An unexpected error occurred."},
            )


ALLOWED_FOR_FILE_UPLOAD: Set[str] = set()


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
    global last_user_activity_lock

    now = utc_now()

    try:
        if is_user_request(request):
            report_user_activity = False
            async with last_user_activity_lock:
                last_user_activity = now
                if (
                    (now - last_user_activity_reported).total_seconds()
                    > DEFAULT_ZENML_SERVER_REPORT_USER_ACTIVITY_TO_DB_SECONDS
                ):
                    last_user_activity_reported = now
                    report_user_activity = True

            if report_user_activity:
                # We don't want to make a DB call here because we're in the
                # context of the asyncio event loop and it would block the
                # entire application for who knows how long.
                # We use the threadpool for it.

                request_context = request_manager().current_request

                def update_last_user_activity_timestamp() -> None:
                    logger.debug(
                        f"[{request_context.log_request_id}] API STATS - "
                        f"{request_context.log_request} "
                        f"UPDATING LAST USER ACTIVITY "
                        f"{get_system_metrics_log_str(request_context.request)}"
                    )

                    try:
                        zen_store()._update_last_user_activity_timestamp(
                            last_user_activity=last_user_activity,
                        )
                    finally:
                        logger.debug(
                            f"[{request_context.log_request_id}] API STATS - "
                            f"{request_context.log_request} "
                            f"UPDATED LAST USER ACTIVITY "
                            f"{get_system_metrics_log_str(request_context.request)}"
                        )

                await to_thread.run_sync(
                    update_last_user_activity_timestamp,
                    limiter=last_user_activity_thread_limiter,
                )

    except Exception as e:
        logger.debug(
            f"An unexpected error occurred while checking user activity: {e}"
        )

    try:
        return await call_next(request)
    except Exception:
        logger.exception("An error occurred while processing the request")
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred."},
        )


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

    try:
        return await call_next(request)
    except Exception:
        logger.exception("An error occurred while processing the request")
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred."},
        )


async def set_secure_headers(request: Request, call_next: Any) -> Any:
    """Middleware to set secure headers.

    Args:
        request: The incoming request.
        call_next: The next function to be called.

    Returns:
        The response with secure headers set.
    """
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("An error occurred while processing the request")
        response = JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred."},
        )

    # If the request is for the openAPI docs, don't set secure headers
    if request.url.path.startswith("/docs") or request.url.path.startswith(
        "/redoc"
    ):
        return response

    secure_headers().framework.fastapi(response)
    return response


async def log_requests(request: Request, call_next: Any) -> Any:
    """Log requests to the ZenML server.

    Args:
        request: The incoming request object.
        call_next: A function that will receive the request as a parameter and
            pass it to the corresponding path operation.

    Returns:
        The response to the request.
    """
    global active_requests_count

    if not logger.isEnabledFor(logging.DEBUG):
        return await call_next(request)

    async with active_requests_lock:
        active_requests_count += 1

    request_context = request_manager().current_request

    logger.debug(
        f"[{request_context.log_request_id}] API STATS - "
        f"{request_context.log_request} "
        f"RECEIVED {get_system_metrics_log_str(request)}"
    )

    try:
        response = await call_next(request)

        logger.debug(
            f"[{request_context.log_request_id}] API STATS - "
            f"{response.status_code} {request_context.log_request} "
            f"took {request_context.log_duration} "
            f"{get_system_metrics_log_str(request)}"
        )

        return response
    finally:
        async with active_requests_lock:
            active_requests_count -= 1


async def record_requests(request: Request, call_next: Any) -> Any:
    """Record requests to the ZenML server.

    Args:
        request: The incoming request object.
        call_next: A function that will receive the request as a parameter and
            pass it to the corresponding path operation.

    Returns:
        The response to the request.
    """
    # Keep track of the request context in a context variable
    request_context = RequestContext(request=request)
    request_manager().current_request = request_context

    try:
        response = await call_next(request)
    except Exception:
        logger.exception("An error occurred while processing the request")
        response = JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred."},
        )

    return response


async def skip_health_middleware(request: Request, call_next: Any) -> Any:
    """Skip health and ready endpoints.

    Args:
        request: The incoming request.
        call_next: The next function to be called.

    Returns:
        The response to the request.
    """
    if request.url.path in [HEALTH, READY]:
        # Skip expensive processing
        return PlainTextResponse("ok")

    return await call_next(request)


def add_middlewares(app: FastAPI) -> None:
    """Add middlewares to the FastAPI app.

    Args:
        app: The FastAPI app.
    """
    app.add_middleware(BaseHTTPMiddleware, dispatch=track_last_user_activity)
    app.add_middleware(BaseHTTPMiddleware, dispatch=infer_source_context)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=server_config().cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(
        RequestBodyLimit,
        max_bytes=server_config().max_request_body_size_in_bytes,
    )
    app.add_middleware(
        RestrictFileUploadsMiddleware, allowed_paths=ALLOWED_FOR_FILE_UPLOAD
    )

    app.add_middleware(BaseHTTPMiddleware, dispatch=set_secure_headers)
    app.add_middleware(BaseHTTPMiddleware, dispatch=log_requests)
    app.add_middleware(BaseHTTPMiddleware, dispatch=record_requests)
    app.add_middleware(BaseHTTPMiddleware, dispatch=skip_health_middleware)
