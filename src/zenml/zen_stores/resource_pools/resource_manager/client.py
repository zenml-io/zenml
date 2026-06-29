#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Synchronous client for the ZenML Pro Resource Manager service."""

from datetime import datetime, timedelta
from threading import RLock
from typing import Any, Optional, Protocol, Type, TypeVar
from uuid import UUID, uuid4

import requests
from pydantic import BaseModel
from requests.adapters import HTTPAdapter, Retry

from zenml.exceptions import (
    CredentialsNotValid,
    EntityExistsError,
    IllegalOperationError,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.resource_pools.resource_manager.transport import (
    RMResourceRequestCreate,
    RMResourceRequestListResponse,
    RMResourceRequestRenewalRequest,
    RMResourceRequestResponse,
)

ModelT = TypeVar("ModelT", bound=BaseModel)


class CloudConnection(Protocol):
    """Protocol for the Cloud API connection used by this client."""

    def get(
        self, endpoint: str, params: Optional[dict[str, Any]]
    ) -> requests.Response:
        """Send a GET request to the Cloud API."""


class ResourceManagerAuthorization(BaseModel):
    """Cloud API response for direct Resource Manager access."""

    token: str
    token_type: str = "bearer"
    resource_manager_id: UUID
    api_url: str
    organization_id: UUID
    workspace_id: Optional[UUID] = None
    expires_at: datetime


class ResourceManagerLoginRequest(BaseModel):
    """Resource Manager login request."""

    organization_id: Optional[UUID] = None
    workspace_id: Optional[UUID] = None


class ResourceManagerLoginResponse(BaseModel):
    """Resource Manager local session response."""

    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    organization_id: UUID
    workspace_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    resource_manager_id: UUID


class ResourceManagerClient:
    """Minimal synchronous client for the Resource Manager REST API."""

    IDEMPOTENCY_HEADER = "X-Idempotency-Key"

    @staticmethod
    def error_message_from_response(response: requests.Response) -> str:
        """Extract a human-readable error message from an RM response.

        Args:
            response: Failed HTTP response from Resource Manager.

        Returns:
            Error message text suitable for ZenML exceptions.
        """
        try:
            payload = response.json()
        except requests.JSONDecodeError:
            return response.text

        if not isinstance(payload, dict):
            return response.text

        detail = payload.get("detail", response.text)
        if isinstance(detail, str):
            return detail
        if isinstance(detail, list):
            return ": ".join(str(item) for item in detail)
        return response.text

    @staticmethod
    def exception_from_rm_response(
        response: requests.Response,
    ) -> Exception:
        """Map a Resource Manager HTTP error to a ZenML store exception.

        Resource Manager returns FastAPI-style ``{"detail": "..."}`` bodies.
        These are translated to the same exception types the workspace REST API
        already maps to HTTP status codes.

        Args:
            response: Failed HTTP response from Resource Manager.

        Returns:
            Exception to raise to workspace callers.
        """
        message = ResourceManagerClient.error_message_from_response(response)
        status_code = response.status_code

        if status_code == 404:
            return KeyError(message)
        if status_code == 409:
            lowered = message.lower()
            if (
                "already exists" in lowered
                or "already registered" in lowered
                or "duplicate" in lowered
            ):
                return EntityExistsError(message)
            return IllegalOperationError(message)
        if status_code in {400, 422}:
            return ValueError(message)
        if status_code == 403:
            return IllegalOperationError(message)
        if status_code == 401:
            return CredentialsNotValid(message)

        return RuntimeError(
            f"{status_code} HTTP Error received from Resource Manager: "
            f"{message}"
        )

    def __init__(
        self,
        *,
        timeout: int = 30,
        headers: Optional[dict[str, str]] = None,
        session: Optional[requests.Session] = None,
        cloud_connection: Optional[CloudConnection] = None,
    ) -> None:
        """Initialize the Resource Manager client.

        Args:
            timeout: Request timeout in seconds.
            headers: Optional headers included with every request.
            session: Optional preconfigured requests session.
            cloud_connection: Optional Cloud API connection override.
        """
        self._base_url: Optional[str] = None
        self._timeout = timeout
        self._session = session or requests.Session()
        self._configure_session(self._session)
        self._headers = headers or {}
        self._cloud_connection = cloud_connection
        self._access_token: Optional[str] = None
        self._access_token_expires_at: Optional[datetime] = None
        self._resource_manager_id: Optional[UUID] = None
        self._organization_id: Optional[UUID] = None
        self._workspace_id: Optional[UUID] = None
        self._lock = RLock()

    def create_request(
        self, request: RMResourceRequestCreate
    ) -> RMResourceRequestResponse:
        """Create a runtime Resource Manager request.

        Args:
            request: Runtime request create payload.

        Returns:
            The created runtime request.
        """
        return self._request_model(
            "POST",
            "/v1/resource-requests",
            RMResourceRequestResponse,
            json=request,
        )

    def get_request(self, request_id: UUID) -> RMResourceRequestResponse:
        """Fetch a runtime Resource Manager request.

        Args:
            request_id: Runtime request ID.

        Returns:
            The requested runtime request.
        """
        return self._request_model(
            "GET",
            f"/v1/resource-requests/{request_id}",
            RMResourceRequestResponse,
        )

    def list_requests(
        self,
        *,
        request_id: Optional[UUID] = None,
        subject_id: Optional[UUID] = None,
        statuses: Optional[list[str]] = None,
        pool_id: Optional[UUID] = None,
        reclaim_tolerance: Optional[str] = None,
        preemption_initiated_by_id: Optional[UUID] = None,
        metadata: Optional[dict[str, str]] = None,
    ) -> RMResourceRequestListResponse:
        """List runtime Resource Manager requests.

        Args:
            request_id: When set, return only the request with this id.
            subject_id: When set, return only requests that include this
                subject id.
            statuses: When set, return only requests in any of these states.
            pool_id: When set, return only requests linked to this pool via an
                allocation or queue entry.
            reclaim_tolerance: When set, return only requests with this
                reclaim tolerance.
            preemption_initiated_by_id: When set, return only requests
                preempted by this request id.
            metadata: Optional exact-match filters against opaque entity
                metadata. Each entry is sent as ``metadata[key]=value``.

        Returns:
            A list wrapper containing matching runtime requests.
        """
        params = self._list_params(
            request_id=request_id,
            subject_id=subject_id,
            statuses=statuses,
            pool=pool_id,
            reclaim_tolerance=reclaim_tolerance,
            preemption_initiated_by_id=preemption_initiated_by_id,
            metadata=metadata,
        )
        return self._request_model(
            "GET",
            "/v1/resource-requests",
            RMResourceRequestListResponse,
            params=params,
        )

    def release_request(self, request_id: UUID) -> RMResourceRequestResponse:
        """Release a runtime Resource Manager request on behalf of its owner.

        Args:
            request_id: Runtime request ID.

        Returns:
            The released runtime request.
        """
        return self._request_model(
            "POST",
            f"/v1/resource-requests/{request_id}/release",
            RMResourceRequestResponse,
        )

    def renew_request(
        self,
        request_id: UUID,
        *,
        lease_expires_at: datetime,
    ) -> RMResourceRequestResponse:
        """Renew a runtime Resource Manager request lease.

        Args:
            request_id: Runtime request ID.
            lease_expires_at: Renewed lease expiration timestamp.

        Returns:
            The renewed runtime request.
        """
        return self._request_model(
            "POST",
            f"/v1/resource-requests/{request_id}/renew",
            RMResourceRequestResponse,
            json=RMResourceRequestRenewalRequest(
                lease_expires_at=lease_expires_at,
            ),
        )

    def _request_model(
        self,
        method: str,
        path: str,
        response_model: Type[ModelT],
        *,
        json: Optional[BaseModel] = None,
        params: Optional[dict[str, str | list[str]]] = None,
    ) -> ModelT:
        """Send an HTTP request and parse a Pydantic response model.

        Args:
            method: HTTP method to use.
            path: API path relative to the Resource Manager base URL.
            response_model: Pydantic model used to parse the response.
            json: Optional Pydantic request body.
            params: Optional query string parameters.

        Returns:
            Parsed response model.
        """
        response = self._request(method, path, json=json, params=params)
        return response_model.model_validate(response.json())

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[BaseModel] = None,
        params: Optional[dict[str, str | list[str]]] = None,
    ) -> requests.Response:
        """Send an HTTP request to the Resource Manager service.

        Args:
            method: HTTP method to use.
            path: API path relative to the Resource Manager base URL.
            json: Optional Pydantic request body.
            params: Optional query string parameters.

        Returns:
            Raw requests response object.

        Raises:
            KeyError: If the server returns 404.
            EntityExistsError: If the server returns 409.
            ValueError: If the server returns 400 or 422.
            IllegalOperationError: If the server returns 403.
            CredentialsNotValid: If the server returns 401.
            RuntimeError: For other HTTP error status codes.
        """  # noqa: DOC503
        payload: Any = None
        if json is not None:
            payload = json.model_dump(mode="json", by_alias=True)

        idempotency_key = str(uuid4())
        headers = self._request_headers(idempotency_key=idempotency_key)
        response = self._session.request(
            method=method,
            url=f"{self._resolved_base_url}{path}",
            headers=headers,
            json=payload,
            params=params,
            timeout=self._timeout,
        )
        if response.status_code == 401:
            self._reset_login()
            headers = self._request_headers(idempotency_key=idempotency_key)
            response = self._session.request(
                method=method,
                url=f"{self._resolved_base_url}{path}",
                headers=headers,
                json=payload,
                params=params,
                timeout=self._timeout,
            )
        if response.status_code >= 400:
            raise self.exception_from_rm_response(response)
        return response

    @property
    def _resolved_base_url(self) -> str:
        """Return the currently known Resource Manager base URL.

        Raises:
            RuntimeError: If no Resource Manager URL is available.

        Returns:
            The Resource Manager base URL.
        """
        if self._base_url is None:
            raise RuntimeError(
                "Resource Manager URL has not been discovered through the "
                "Cloud API authorization exchange."
            )
        return self._base_url

    def _request_headers(self, *, idempotency_key: str) -> dict[str, str]:
        """Build headers for a Resource Manager request.

        Args:
            idempotency_key: Idempotency key to send with this request.

        Returns:
            HTTP headers for the request.
        """
        headers = {
            **self._headers,
            self.IDEMPOTENCY_HEADER: idempotency_key,
        }
        headers["Authorization"] = f"Bearer {self._fetch_access_token()}"
        return headers

    def _fetch_access_token(self) -> str:
        """Fetch or refresh the Resource Manager local access token.

        Returns:
            A Resource Manager bearer token.
        """
        with self._lock:
            if (
                self._access_token is not None
                and self._access_token_expires_at is not None
                and utc_now(tz_aware=self._access_token_expires_at)
                + timedelta(minutes=5)
                < self._access_token_expires_at
            ):
                return self._access_token

            authorization = self._fetch_authorization()
            self._base_url = authorization.api_url.rstrip("/")
            login = self._login_to_resource_manager(authorization)

            self._access_token = login.access_token
            self._access_token_expires_at = login.expires_at
            self._resource_manager_id = login.resource_manager_id
            self._organization_id = login.organization_id
            self._workspace_id = login.workspace_id
            return self._access_token

    def _reset_login(self) -> None:
        """Force a new Resource Manager login on the next request."""
        with self._lock:
            self._access_token = None
            self._access_token_expires_at = None

    def _fetch_authorization(self) -> ResourceManagerAuthorization:
        """Fetch Resource Manager discovery and one-time auth from Cloud API.

        Returns:
            Cloud API authorization response.

        Raises:
            RuntimeError: If Cloud API returns an invalid authorization
                response.
        """
        cloud_connection = self._cloud_connection
        if cloud_connection is None:
            from zenml.zen_server.cloud_utils import (
                cloud_connection as connect,
            )

            cloud_connection = self._cloud_connection = connect()

        response = cloud_connection.get(
            "/auth/resource_manager_authorization",
            params=None,
        )
        try:
            return ResourceManagerAuthorization.model_validate(response.json())
        except Exception as e:
            raise RuntimeError(
                "Could not fetch Resource Manager authorization from the "
                f"Cloud API: {e}"
            )

    def _login_to_resource_manager(
        self, authorization: ResourceManagerAuthorization
    ) -> ResourceManagerLoginResponse:
        """Exchange a Cloud API one-time token for an RM-local session.

        Args:
            authorization: Cloud API authorization response.

        Raises:
            self.exception_from_rm_response: If Resource Manager rejects the
                login request.
            RuntimeError: If the RM returns an invalid login response.

        Returns:
            Resource Manager local session response.
        """
        login_request = ResourceManagerLoginRequest(
            organization_id=authorization.organization_id,
            workspace_id=authorization.workspace_id,
        )
        response = self._session.post(
            f"{self._resolved_base_url}/v1/auth/login",
            headers={
                "Authorization": f"Bearer {authorization.token}",
            },
            json=login_request.model_dump(mode="json"),
            timeout=self._timeout,
        )
        if response.status_code >= 400:
            raise self.exception_from_rm_response(response)

        try:
            return ResourceManagerLoginResponse.model_validate(response.json())
        except Exception as e:
            raise RuntimeError(
                f"Could not log in to the Resource Manager API: {e}"
            )

    def _configure_session(self, session: requests.Session) -> None:
        """Configure session retry behavior for transient HTTP failures.

        This mirrors the REST ZenStore client behavior so transient network
        and upstream availability issues are retried consistently.

        Args:
            session: Session to configure.
        """
        retries = Retry(
            connect=5,
            read=8,
            redirect=3,
            status=10,
            allowed_methods=[
                "HEAD",
                "GET",
                "POST",
                "PUT",
                "PATCH",
                "DELETE",
                "OPTIONS",
            ],
            status_forcelist=[
                408,  # Request Timeout
                429,  # Too Many Requests
                502,  # Bad Gateway
                503,  # Service Unavailable
                504,  # Gateway Timeout
            ],
            other=3,
            backoff_factor=1,
        )
        http_adapter = HTTPAdapter(max_retries=retries)
        session.mount("https://", http_adapter)
        session.mount("http://", http_adapter)

    @staticmethod
    def _list_params(**values: object) -> Optional[dict[str, str | list[str]]]:
        """Build optional query parameters for list endpoints.

        Scalar values become one query parameter. Sequence values become
        repeated query parameters. Mapping values become ``field[key]=value``
        bracket query parameters.

        Args:
            **values: Optional filter values keyed by query parameter name.

        Returns:
            Query parameters with unset values omitted, or ``None`` when empty.
        """
        params: dict[str, str | list[str]] = {}
        for key, value in values.items():
            if value is None:
                continue
            if isinstance(value, dict):
                for inner_key, inner_value in value.items():
                    params[f"{key}[{inner_key}]"] = str(inner_value)
                continue
            if isinstance(value, (list, tuple)):
                params[key] = [str(entry) for entry in value]
                continue
            params[key] = str(value)
        return params or None
