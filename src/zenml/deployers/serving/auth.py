#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Authentication middleware for ZenML Pipeline Serving."""

import os
from typing import Awaitable, Callable, Set

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_401_UNAUTHORIZED
from starlette.types import ASGIApp

from zenml.logger import get_logger

logger = get_logger(__name__)

# Endpoints that don't require authentication
UNPROTECTED_ENDPOINTS: Set[str] = {
    "/",
    "/health",
    "/info",
    "/metrics",
    "/status",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class BearerTokenAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for optional bearer token authentication.

    This middleware implements a clean separation of concerns:
    - Authentication is handled centrally via middleware
    - Configuration is environment-driven
    - Public endpoints remain accessible
    - Error responses are standardized

    Following the principle of fail-safe defaults, if no auth key is configured,
    all endpoints remain accessible.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Initialize authentication middleware.

        Args:
            app: FastAPI application instance
        """
        super().__init__(app)
        self._auth_key = os.getenv("ZENML_SERVING_AUTH_KEY", "").strip()
        self._auth_enabled = (
            self._auth_key is not None and self._auth_key != ""
        )

        if self._auth_enabled:
            logger.info("🔒 Bearer token authentication enabled")
        else:
            logger.info(
                "🔓 Authentication disabled - all endpoints accessible"
            )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process request and apply authentication if required.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in the chain

        Returns:
            HTTP response

        Raises:
            HTTPException: For authentication failures
        """
        # Early return for unprotected endpoints
        if self._is_unprotected_endpoint(request.url.path):
            return await call_next(request)

        # If authentication is not enabled, allow all requests
        if not self._auth_enabled:
            return await call_next(request)

        # Validate bearer token for protected endpoints
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning(
                f"Unauthorized access attempt to {request.url.path} - "
                "missing Authorization header"
            )
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Authorization header required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extract and validate bearer token
        if not auth_header.startswith("Bearer "):
            logger.warning(
                f"Unauthorized access attempt to {request.url.path} - "
                "invalid Authorization format"
            )
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization format. Expected: Bearer <token>",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header[7:]  # Remove "Bearer " prefix
        if token != self._auth_key:
            logger.warning(
                f"Unauthorized access attempt to {request.url.path} - "
                "invalid token"
            )
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Token is valid, proceed with request
        return await call_next(request)

    def _is_unprotected_endpoint(self, path: str) -> bool:
        """Check if an endpoint is unprotected.

        Args:
            path: Request path to check

        Returns:
            True if endpoint should be accessible without authentication
        """
        # Exact match for unprotected endpoints
        if path in UNPROTECTED_ENDPOINTS:
            return True

        # Handle trailing slashes gracefully
        normalized_path = path.rstrip("/")
        if normalized_path in UNPROTECTED_ENDPOINTS:
            return True

        return False
