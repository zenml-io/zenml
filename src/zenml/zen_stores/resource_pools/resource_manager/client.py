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

from typing import Any, Optional, Type, TypeVar
from uuid import UUID, uuid4

import requests
from pydantic import BaseModel
from requests.adapters import HTTPAdapter, Retry

from zenml.exceptions import (
    CredentialsNotValid,
    EntityExistsError,
    IllegalOperationError,
)
from zenml.zen_stores.resource_pools.resource_manager.transport import (
    RMAllocationListResponse,
    RMPolicyListResponse,
    RMPolicyRequest,
    RMPolicyResponse,
    RMPolicyUpdate,
    RMPoolListResponse,
    RMPoolRequest,
    RMPoolResponse,
    RMPoolUpdate,
    RMQueueEntryListResponse,
    RMResourceListResponse,
    RMResourceRequest,
    RMResourceRequestCreate,
    RMResourceRequestListResponse,
    RMResourceRequestResponse,
    RMResourceResponse,
    RMResourceUpdate,
)

ModelT = TypeVar("ModelT", bound=BaseModel)


def _error_message_from_response(response: requests.Response) -> str:
    """Extract a human-readable error message from a Resource Manager response.

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


def _exception_from_rm_response(response: requests.Response) -> Exception:
    """Map a Resource Manager HTTP error to a ZenML store exception.

    Resource Manager returns FastAPI-style ``{"detail": "..."}`` bodies. These
    are translated to the same exception types the workspace REST API already
    maps to HTTP status codes.

    Args:
        response: Failed HTTP response from Resource Manager.

    Returns:
        Exception to raise to workspace callers.
    """
    message = _error_message_from_response(response)
    status_code = response.status_code

    if status_code == 404:
        return KeyError(message)
    if status_code == 409:
        return EntityExistsError(message)
    if status_code in {400, 422}:
        return ValueError(message)
    if status_code == 403:
        return IllegalOperationError(message)
    if status_code == 401:
        return CredentialsNotValid(message)

    return RuntimeError(
        f"{status_code} HTTP Error received from Resource Manager: {message}"
    )


class ResourceManagerClient:
    """Minimal synchronous client for the Resource Manager REST API."""

    IDEMPOTENCY_HEADER = "X-Idempotency-Key"
    ORGANIZATION_HEADER = "X-Test-Organization-Id"

    def __init__(
        self,
        base_url: str,
        *,
        timeout: int = 30,
        headers: Optional[dict[str, str]] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        """Initialize the Resource Manager client.

        Args:
            base_url: Base URL of the Resource Manager service.
            timeout: Request timeout in seconds.
            headers: Optional headers included with every request.
            session: Optional preconfigured requests session.
        """
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = session or requests.Session()
        self._configure_session(self._session)
        self._headers = headers or {}

    def create_resource(
        self, request: RMResourceRequest
    ) -> RMResourceResponse:
        """Create a Resource Manager resource descriptor.

        Args:
            request: Descriptor create payload.

        Returns:
            The created descriptor.
        """
        return self._request_model(
            "POST", "/v1/resources", RMResourceResponse, json=request
        )

    def get_resource(self, resource_id: UUID) -> RMResourceResponse:
        """Fetch a Resource Manager resource descriptor.

        Args:
            resource_id: Descriptor ID.

        Returns:
            The requested descriptor.
        """
        return self._request_model(
            "GET", f"/v1/resources/{resource_id}", RMResourceResponse
        )

    def list_resources(
        self,
        *,
        resource_id: Optional[UUID] = None,
        name: Optional[str] = None,
        metadata: Optional[dict[str, str]] = None,
    ) -> RMResourceListResponse:
        """List Resource Manager resource descriptors.

        Args:
            resource_id: When set, return only the descriptor with this id.
            name: When set, return only descriptors with this exact name.
            metadata: Optional exact-match filters against opaque entity
                metadata. Each entry is sent as a query parameter.

        Returns:
            A list wrapper containing matching descriptors.
        """
        params = self._list_params(
            metadata=metadata,
            resource_id=resource_id,
            name=name,
        )
        return self._request_model(
            "GET", "/v1/resources", RMResourceListResponse, params=params
        )

    def update_resource(
        self, resource_id: UUID, update: RMResourceUpdate
    ) -> RMResourceResponse:
        """Update a Resource Manager resource descriptor.

        Args:
            resource_id: Descriptor ID.
            update: Descriptor update payload.

        Returns:
            The updated descriptor.
        """
        return self._request_model(
            "PATCH",
            f"/v1/resources/{resource_id}",
            RMResourceResponse,
            json=update,
        )

    def delete_resource(self, resource_id: UUID) -> None:
        """Delete a Resource Manager resource descriptor.

        Args:
            resource_id: Descriptor ID.
        """
        self._request("DELETE", f"/v1/resources/{resource_id}")

    def create_pool(self, request: RMPoolRequest) -> RMPoolResponse:
        """Create a Resource Manager resource pool.

        Args:
            request: Pool create payload.

        Returns:
            The created pool.
        """
        return self._request_model(
            "POST", "/v1/resource-pools", RMPoolResponse, json=request
        )

    def get_pool(self, pool_id: UUID) -> RMPoolResponse:
        """Fetch a Resource Manager resource pool.

        Args:
            pool_id: Pool ID.

        Returns:
            The requested pool.
        """
        return self._request_model(
            "GET", f"/v1/resource-pools/{pool_id}", RMPoolResponse
        )

    def list_pools(
        self,
        *,
        pool_id: Optional[UUID] = None,
        name: Optional[str] = None,
        metadata: Optional[dict[str, str]] = None,
    ) -> RMPoolListResponse:
        """List Resource Manager resource pools.

        Args:
            pool_id: When set, return only the pool with this id.
            name: When set, return only pools with this exact name.
            metadata: Optional exact-match filters against opaque entity
                metadata. Each entry is sent as a query parameter.

        Returns:
            A list wrapper containing matching pools.
        """
        params = self._list_params(
            metadata=metadata,
            pool_id=pool_id,
            name=name,
        )
        return self._request_model(
            "GET", "/v1/resource-pools", RMPoolListResponse, params=params
        )

    def update_pool(
        self, pool_id: UUID, update: RMPoolUpdate
    ) -> RMPoolResponse:
        """Update a Resource Manager resource pool.

        Args:
            pool_id: Pool ID.
            update: Pool update payload.

        Returns:
            The updated pool.
        """
        return self._request_model(
            "PATCH",
            f"/v1/resource-pools/{pool_id}",
            RMPoolResponse,
            json=update,
        )

    def delete_pool(self, pool_id: UUID) -> None:
        """Delete a Resource Manager resource pool.

        Args:
            pool_id: Pool ID.
        """
        self._request("DELETE", f"/v1/resource-pools/{pool_id}")

    def list_pool_queue(self, pool_id: UUID) -> RMQueueEntryListResponse:
        """List queue entries for a Resource Manager pool.

        Args:
            pool_id: Pool ID.

        Returns:
            Queue entries for the pool.
        """
        return self._request_model(
            "GET",
            f"/v1/resource-pools/{pool_id}/queue",
            RMQueueEntryListResponse,
        )

    def list_pool_allocations(self, pool_id: UUID) -> RMAllocationListResponse:
        """List allocations for a Resource Manager pool.

        Args:
            pool_id: Pool ID.

        Returns:
            Active and historical allocations for the pool.
        """
        return self._request_model(
            "GET",
            f"/v1/resource-pools/{pool_id}/allocations",
            RMAllocationListResponse,
        )

    def list_policies(
        self,
        *,
        policy_id: Optional[UUID] = None,
        pool_id: Optional[UUID] = None,
        pool: Optional[str] = None,
        subject_id: Optional[UUID] = None,
        priority: Optional[int] = None,
        metadata: Optional[dict[str, str]] = None,
    ) -> RMPolicyListResponse:
        """List Resource Manager policies.

        Args:
            policy_id: When set, return only the policy with this id.
            pool_id: When set, return only policies bound to this pool id.
            pool: When set, return only policies bound to this pool name.
            subject_id: When set, return only policies whose selector
                references this subject id.
            priority: When set, return only policies with this exact priority.
            metadata: Optional exact-match filters against opaque entity
                metadata. Each entry is sent as a query parameter.

        Returns:
            A list wrapper containing matching policies.
        """
        params = self._list_params(
            metadata=metadata,
            policy_id=policy_id,
            pool_id=pool_id,
            pool=pool,
            subject_id=subject_id,
            priority=priority,
        )
        return self._request_model(
            "GET",
            "/v1/resource-policies",
            RMPolicyListResponse,
            params=params,
        )

    def create_policy(self, request: RMPolicyRequest) -> RMPolicyResponse:
        """Create a Resource Manager policy.

        Args:
            request: Policy create payload.

        Returns:
            The created policy.
        """
        return self._request_model(
            "POST", "/v1/resource-policies", RMPolicyResponse, json=request
        )

    def get_policy(self, policy_id: UUID) -> RMPolicyResponse:
        """Fetch a Resource Manager policy.

        Args:
            policy_id: Policy ID.

        Returns:
            The requested policy.
        """
        return self._request_model(
            "GET", f"/v1/resource-policies/{policy_id}", RMPolicyResponse
        )

    def update_policy(
        self, policy_id: UUID, update: RMPolicyUpdate
    ) -> RMPolicyResponse:
        """Update a Resource Manager policy.

        Args:
            policy_id: Policy ID.
            update: Policy update payload.

        Returns:
            The updated policy.
        """
        return self._request_model(
            "PATCH",
            f"/v1/resource-policies/{policy_id}",
            RMPolicyResponse,
            json=update,
        )

    def delete_policy(self, policy_id: UUID) -> None:
        """Delete a Resource Manager policy.

        Args:
            policy_id: Policy ID.
        """
        self._request("DELETE", f"/v1/resource-policies/{policy_id}")

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
        status: Optional[str] = None,
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
            status: When set, return only requests in this lifecycle state.
            statuses: When set, return only requests in any of these states.
            pool_id: When set, return only requests linked to this pool via an
                allocation or queue entry.
            reclaim_tolerance: When set, return only requests with this
                reclaim tolerance.
            preemption_initiated_by_id: When set, return only requests
                preempted by this request id.
            metadata: Optional exact-match filters against opaque entity
                metadata. Each entry is sent as a query parameter.

        Returns:
            A list wrapper containing matching runtime requests.
        """
        params = self._list_params(
            metadata=metadata,
            request_id=request_id,
            subject_id=subject_id,
            status=status,
            statuses=statuses,
            pool_id=pool_id,
            reclaim_tolerance=reclaim_tolerance,
            preemption_initiated_by_id=preemption_initiated_by_id,
        )
        return self._request_model(
            "GET",
            "/v1/resource-requests",
            RMResourceRequestListResponse,
            params=params,
        )

    def release_request(self, request_id: UUID) -> RMResourceRequestResponse:
        """Release a runtime Resource Manager request.

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

    def cancel_request(self, request_id: UUID) -> RMResourceRequestResponse:
        """Cancel a runtime Resource Manager request.

        Args:
            request_id: Runtime request ID.

        Returns:
            The canceled runtime request.
        """
        return self._request_model(
            "POST",
            f"/v1/resource-requests/{request_id}/cancel",
            RMResourceRequestResponse,
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

        headers = {
            **self._headers,
            self.IDEMPOTENCY_HEADER: str(uuid4()),
        }
        response = self._session.request(
            method=method,
            url=f"{self._base_url}{path}",
            headers=headers,
            json=payload,
            params=params,
            timeout=self._timeout,
        )
        if response.status_code >= 400:
            raise _exception_from_rm_response(response)
        return response

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
    def _list_params(
        *,
        metadata: Optional[dict[str, str]] = None,
        **values: object,
    ) -> Optional[dict[str, str | list[str]]]:
        """Build optional query parameters for list endpoints.

        Args:
            metadata: Optional exact-match opaque metadata filters merged
                into the query string as individual parameters.
            **values: Optional filter values keyed by query parameter name.

        Returns:
            Query parameters with unset values omitted, or ``None`` when empty.
        """
        params: dict[str, str | list[str]] = {}
        for key, value in values.items():
            if value is None:
                continue
            if isinstance(value, (list, tuple)):
                params[key] = [str(entry) for entry in value]
                continue
            params[key] = str(value)
        if metadata:
            params.update(metadata)
        return params or None
