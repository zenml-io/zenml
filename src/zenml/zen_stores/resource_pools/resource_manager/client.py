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
    RMSubjectRequest,
    RMSubjectResponse,
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

    def list_resources(self) -> RMResourceListResponse:
        """List Resource Manager resource descriptors.

        Returns:
            A list wrapper containing all descriptors.
        """
        return self._request_model(
            "GET", "/v1/resources", RMResourceListResponse
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

    def list_pools(self) -> RMPoolListResponse:
        """List Resource Manager resource pools.

        Returns:
            A list wrapper containing all pools.
        """
        return self._request_model(
            "GET", "/v1/resource-pools", RMPoolListResponse
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

    def get_subject(self, subject_id: UUID) -> RMSubjectResponse:
        """Fetch an internal Resource Manager subject.

        Args:
            subject_id: Subject ID.

        Returns:
            The requested subject.
        """
        return self._request_model(
            "GET", f"/v1/subjects/{subject_id}", RMSubjectResponse
        )

    def create_subject(self, request: RMSubjectRequest) -> RMSubjectResponse:
        """Create an internal Resource Manager subject.

        Args:
            request: Subject create payload.

        Returns:
            The created subject.
        """
        return self._request_model(
            "POST", "/v1/subjects", RMSubjectResponse, json=request
        )

    def update_subject(
        self, subject_id: UUID, request: RMSubjectRequest
    ) -> RMSubjectResponse:
        """Update an internal Resource Manager subject.

        Args:
            subject_id: Subject ID.
            request: Subject update payload.

        Returns:
            The updated subject.
        """
        return self._request_model(
            "PATCH",
            f"/v1/subjects/{subject_id}",
            RMSubjectResponse,
            json=request,
        )

    def delete_subject(self, subject_id: UUID) -> None:
        """Delete an internal Resource Manager subject.

        Args:
            subject_id: Subject ID.
        """
        self._request("DELETE", f"/v1/subjects/{subject_id}")

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

    def list_policies(self) -> RMPolicyListResponse:
        """List Resource Manager policies.

        Returns:
            A list wrapper containing all policies.
        """
        return self._request_model(
            "GET", "/v1/resource-policies", RMPolicyListResponse
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

    def list_requests(self) -> RMResourceRequestListResponse:
        """List runtime Resource Manager requests.

        Returns:
            A list wrapper containing all runtime requests.
        """
        return self._request_model(
            "GET",
            "/v1/resource-requests",
            RMResourceRequestListResponse,
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
    ) -> ModelT:
        """Send an HTTP request and parse a Pydantic response model.

        Args:
            method: HTTP method to use.
            path: API path relative to the Resource Manager base URL.
            response_model: Pydantic model used to parse the response.
            json: Optional Pydantic request body.

        Returns:
            Parsed response model.
        """
        response = self._request(method, path, json=json)
        return response_model.model_validate(response.json())

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[BaseModel] = None,
    ) -> requests.Response:
        """Send an HTTP request to the Resource Manager service.

        Args:
            method: HTTP method to use.
            path: API path relative to the Resource Manager base URL.
            json: Optional Pydantic request body.

        Returns:
            Raw requests response object.
        """
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
