"""Management and service-key inference clients for managed model services."""

import json
import time
from contextlib import contextmanager
from typing import Any, Iterator, List, Optional
from urllib.parse import urlsplit
from uuid import UUID

import requests

from zenml.models.managed_model import (
    ManagedModelContract,
    ManagedModelInferenceKey,
    ManagedModelMutation,
    ManagedModelService,
    ManagedModelServicePage,
    ManagedModelServiceRequest,
)
from zenml.zen_stores.rest_zen_store import RestZenStore


class ManagedModelClient:
    """Submit durable intents and inspect progress through one workspace API."""

    def __init__(self, store: Optional[RestZenStore] = None) -> None:
        """Bind to an authenticated remote workspace.

        Args:
            store: Explicit workspace transport, or the active client store.

        Raises:
            ValueError: If the active store is not a remote workspace.
        """
        if store is None:
            from zenml.client import Client

            active = Client().zen_store
            if not isinstance(active, RestZenStore):
                raise ValueError(
                    "Managed serving requires a remote workspace."
                )
            store = active
        self.store = store

    def create(
        self, request: ManagedModelServiceRequest, request_key: str
    ) -> ManagedModelService:
        """Accept one deployment intent using a caller-stable retry key.

        Args:
            request: Artifact package, project and deployer references.
            request_key: Key reused for retries of exactly this intent.

        Returns:
            Accepted service; acceptance does not mean inference is ready.
        """
        return ManagedModelService.model_validate(
            self.store.post(
                "/managed-model-services",
                body=request,
                headers={"Idempotency-Key": request_key},
            )
        )

    def get(self, service_id: UUID) -> ManagedModelService:
        """Read a stable service and its current operation.

        Args:
            service_id: Service ID returned by creation.

        Returns:
            Public service progress.
        """
        return ManagedModelService.model_validate(
            self.store.get(f"/managed-model-services/{service_id}")
        )

    def list(
        self, project_id: UUID, offset: int = 0, limit: int = 50
    ) -> ManagedModelServicePage:
        """List an explicitly selected project.

        Args:
            project_id: Project to query.
            offset: Page offset.
            limit: Maximum page size, up to 100.

        Returns:
            Authorized service page.
        """
        return ManagedModelServicePage.model_validate(
            self.store.get(
                "/managed-model-services",
                params={
                    "project_id": str(project_id),
                    "offset": offset,
                    "limit": limit,
                },
            )
        )

    def mutate(
        self, service_id: UUID, request: ManagedModelMutation, request_key: str
    ) -> ManagedModelService:
        """Accept update, rollback, pause, resume or delete with concurrency control.

        Args:
            service_id: Target service.
            request: Mutation including the caller's observed generation.
            request_key: Key reused for retries of exactly this mutation.

        Returns:
            Accepted operation and public service state.
        """
        return ManagedModelService.model_validate(
            self.store.post(
                f"/managed-model-services/{service_id}/operations",
                body=request,
                headers={"Idempotency-Key": request_key},
            )
        )

    def wait(
        self,
        service: ManagedModelService,
        timeout: float = 600,
        poll_interval: float = 5,
    ) -> ManagedModelService:
        """Wait for the accepted operation without canceling work on timeout.

        Args:
            service: Accepted service and operation to observe.
            timeout: Local waiting budget in seconds.
            poll_interval: Delay between status requests.

        Returns:
            Service after the requested operation succeeds.

        Raises:
            ValueError: If waiting parameters are invalid.
            RuntimeError: If the operation fails, is uncertain or is superseded.
            TimeoutError: If the local wait expires; server work continues.
        """
        if timeout < 0 or poll_interval <= 0:
            raise ValueError(
                "Use a nonnegative timeout and positive poll interval."
            )
        deadline = time.monotonic() + timeout
        while True:
            current = self.get(service.id)
            if current.operation.id != service.operation.id:
                raise RuntimeError(
                    f"Service {service.id} has a newer operation; inspect it before continuing."
                )
            if current.operation.status == "succeeded":
                return current
            if current.operation.status in ("failed", "uncertain"):
                raise RuntimeError(
                    f"Service {service.id}: {current.operation.error or current.operation.status}"
                )
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"Service {service.id} is still running operation {service.operation.id}; poll it again."
                )
            time.sleep(min(poll_interval, remaining))

    def purge(self, service_id: UUID) -> None:
        """Remove a completed tombstone after owned provider cleanup succeeds.

        Args:
            service_id: Fully deleted service whose project/component references can be released.
        """
        self.store.delete(f"/managed-model-services/{service_id}/record")

    def rotate_inference_key(
        self, service_id: UUID
    ) -> ManagedModelInferenceKey:
        """Issue a key once and invalidate any previously issued key.

        Args:
            service_id: Service to authorize independently of a ZenML login.

        Returns:
            Plaintext credential to store securely outside pipeline artifacts.
        """
        return ManagedModelInferenceKey.model_validate(
            self.store.post(
                f"/managed-model-services/{service_id}/inference-key",
                body=ManagedModelContract(),
            )
        )

    def revoke_inference_key(self, service_id: UUID) -> None:
        """Disable new inference requests for the service.

        Args:
            service_id: Service whose inference credential is revoked.
        """
        self.store.delete(
            f"/managed-model-services/{service_id}/inference-key"
        )


class ManagedModelInferenceClient:
    """Invoke one managed model using its URL and service-specific key."""

    def __init__(self, prediction_url: str, api_key: str) -> None:
        """Configure inference without a ZenML workspace login.

        Args:
            prediction_url: HTTPS prediction URL returned by the service.
            api_key: Service-specific inference key, not a ZenML access token.

        Raises:
            ValueError: If the URL or key is invalid.
        """
        parsed = urlsplit(prediction_url)
        parts = parsed.path.strip("/").split("/")
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or len(parts) != 2
            or parts[0] != "models"
        ):
            raise ValueError("Use the service's HTTPS prediction URL.")
        self.service_id = UUID(parts[1])
        if not api_key or "\n" in api_key or "\r" in api_key:
            raise ValueError("An inference key is required.")
        self.prediction_url = prediction_url.rstrip("/")
        self._api_key = api_key

    def predict(
        self,
        messages: List[dict[str, Any]],
        **parameters: Any,
    ) -> dict[str, Any]:
        """Invoke the active revision through the authenticated workspace gateway.

        Args:
            messages: OpenAI-compatible chat messages.
            **parameters: Additional inference options such as max_tokens.

        Returns:
            Parsed chat-completion response.

        Raises:
            RuntimeError: If the gateway does not return a JSON object.
        """
        with self._open_inference(messages, False, parameters) as response:
            value = response.json()
            if not isinstance(value, dict):
                raise RuntimeError("Invalid inference response.")
            return value

    def stream(
        self,
        messages: List[dict[str, Any]],
        **parameters: Any,
    ) -> Iterator[dict[str, Any]]:
        """Yield incremental chat-completion events without retrying generated work.

        Args:
            messages: OpenAI-compatible chat messages.
            **parameters: Additional inference options such as max_tokens.

        Yields:
            Parsed data events from the selected service.

        Raises:
            RuntimeError: If the stream reports an error or invalid data.
        """
        with self._open_inference(messages, True, parameters) as response:
            for line in response.iter_lines(chunk_size=1, decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    return
                try:
                    event = json.loads(payload)
                except ValueError:
                    raise RuntimeError(
                        "Invalid inference stream event."
                    ) from None
                if not isinstance(event, dict) or "error" in event:
                    raise RuntimeError("Inference stream interrupted.")
                yield event
            raise RuntimeError("Inference stream ended before completion.")

    @contextmanager
    def _open_inference(
        self,
        messages: List[dict[str, Any]],
        stream: bool,
        parameters: dict[str, Any],
    ) -> Iterator[requests.Response]:
        """Open one inference request against the exact workspace-owned URL.

        Args:
            messages: Chat messages.
            stream: Whether incremental events are requested.
            parameters: Additional provider-supported request options.

        Yields:
            An open response that is closed on completion or consumer exit.

        Raises:
            RuntimeError: If the request is rejected or interrupted.
        """
        body = {
            **parameters,
            "model": str(self.service_id),
            "messages": messages,
            "stream": stream,
        }
        try:
            with requests.Session() as session:
                session.trust_env = False
                with session.post(
                    self.prediction_url + "/v1/chat/completions",
                    json=body,
                    headers={"Authorization": "Bearer " + self._api_key},
                    stream=True,
                    timeout=(5, 180),
                    allow_redirects=False,
                ) as response:
                    if response.status_code != 200:
                        raise RuntimeError(
                            f"Inference gateway returned HTTP {response.status_code}."
                        )
                    yield response
        except requests.RequestException:
            raise RuntimeError(
                "Inference transport failed; generation was not automatically retried."
            ) from None
