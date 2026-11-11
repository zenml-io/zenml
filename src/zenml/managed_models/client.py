"""Credential-free SDK for the workspace managed serving API."""

import json
import time
from contextlib import contextmanager
from typing import Any, Iterator, List, Optional
from uuid import UUID

import requests

from zenml.models.managed_model import (
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

    def predict(
        self,
        service_id: UUID,
        messages: List[dict[str, Any]],
        **parameters: Any,
    ) -> dict[str, Any]:
        """Invoke the active revision through the authenticated workspace gateway.

        Args:
            service_id: Ready service identity.
            messages: OpenAI-compatible chat messages.
            **parameters: Additional inference options such as max_tokens.

        Returns:
            Parsed chat-completion response.

        Raises:
            RuntimeError: If the gateway does not return a JSON object.
        """
        with self._open_inference(
            service_id, messages, False, parameters
        ) as response:
            value = response.json()
            if not isinstance(value, dict):
                raise RuntimeError("Invalid inference response.")
            return value

    def stream(
        self,
        service_id: UUID,
        messages: List[dict[str, Any]],
        **parameters: Any,
    ) -> Iterator[dict[str, Any]]:
        """Yield incremental chat-completion events without retrying generated work.

        Args:
            service_id: Ready service identity.
            messages: OpenAI-compatible chat messages.
            **parameters: Additional inference options such as max_tokens.

        Yields:
            Parsed data events from the selected service.

        Raises:
            RuntimeError: If the stream reports an error or invalid data.
        """
        with self._open_inference(
            service_id, messages, True, parameters
        ) as response:
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
        service_id: UUID,
        messages: List[dict[str, Any]],
        stream: bool,
        parameters: dict[str, Any],
    ) -> Iterator[requests.Response]:
        """Open one inference request against the exact workspace-owned URL.

        Args:
            service_id: Stable service identity.
            messages: Chat messages.
            stream: Whether incremental events are requested.
            parameters: Additional provider-supported request options.

        Yields:
            An open response that is closed on completion or consumer exit.

        Raises:
            ValueError: If the service is not ready or its URL is not trusted.
            RuntimeError: If the request is rejected or interrupted.
        """
        service = self.get(service_id)
        expected = self.store.url.rstrip("/") + f"/models/{service_id}"
        if (
            service.state != "ready"
            or service.desired_state != "running"
            or service.prediction_url != expected
            or not expected.startswith("https://")
        ):
            raise ValueError(
                "Service must be ready at its trusted HTTPS workspace inference URL."
            )
        body = {
            **parameters,
            "model": str(service_id),
            "messages": messages,
            "stream": stream,
        }
        try:
            with requests.Session() as session:
                session.trust_env = False
                with session.post(
                    expected + "/v1/chat/completions",
                    json=body,
                    headers={
                        "Authorization": "Bearer "
                        + self.store.get_or_generate_api_token()
                    },
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
