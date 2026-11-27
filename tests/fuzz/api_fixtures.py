#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Authenticated HTTP fixtures for API fuzz tests."""

from contextlib import contextmanager
from dataclasses import dataclass, replace
from typing import Any, Generator, Mapping, Optional, cast
from uuid import uuid4

import requests
from tests.fuzz.api_server import REQUEST_TIMEOUT_SECONDS, RunningApiServer

_BASELINE_TAGS = {
    "primary": {"name": "fuzz-primary", "color": "grey"},
    "secondary": {"name": "fuzz-secondary", "color": "blue"},
}
MAX_TAG_RESET_ROUNDS = 10


@dataclass(frozen=True)
class BaselineIds:
    """Stable logical names and current physical IDs for the API baseline."""

    project_id: str
    pipeline_id: str
    snapshot_id: str
    run_id: str
    tag_ids: Mapping[str, str]


class ApiHarness:
    """Authenticated client and isolated baseline for generated API examples."""

    def __init__(self, server: RunningApiServer) -> None:
        """Initialize a client bound to one disposable server.

        Args:
            server: Authenticated disposable server used by this harness.
        """
        self.server = server
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Accept": "application/json",
                "Authorization": f"Bearer {server.token}",
            }
        )
        self._baseline: Optional[BaselineIds] = None
        self._tags_dirty = False
        self._contaminated = False

    def request(
        self,
        method: str,
        path: str,
        *,
        expected_status: Optional[int] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Send one authenticated request and optionally assert its status.

        Args:
            method: HTTP method.
            path: Absolute API path relative to the disposable server.
            expected_status: Exact response status required by the caller.
            **kwargs: Additional arguments passed to ``requests.Session.request``.

        Returns:
            The HTTP response.

        Raises:
            RuntimeError: If the harness is contaminated or status mismatches.
        """
        if self._contaminated:
            raise RuntimeError(
                "API harness cannot be reused after a restoration failure"
            )
        response = self._session.request(
            method,
            self._url(path),
            timeout=REQUEST_TIMEOUT_SECONDS,
            **kwargs,
        )
        if (
            expected_status is not None
            and response.status_code != expected_status
        ):
            raise RuntimeError(
                f"{method.upper()} {path} returned {response.status_code}, "
                f"expected {expected_status}: {response.text[:1000]}"
            )
        return response

    def request_json(
        self,
        method: str,
        path: str,
        *,
        expected_status: int = 200,
        **kwargs: Any,
    ) -> Any:
        """Send an authenticated request and decode its JSON response.

        Args:
            method: HTTP method.
            path: Absolute API path relative to the disposable server.
            expected_status: Exact response status required by the caller.
            **kwargs: Additional arguments passed to ``request``.

        Returns:
            Decoded JSON payload.
        """
        response = self.request(
            method, path, expected_status=expected_status, **kwargs
        )
        return response.json()

    def call_case(self, case: Any) -> requests.Response:
        """Execute a Schemathesis case with fixed authentication and tracing.

        Args:
            case: Schemathesis case generated from the live server schema.

        Returns:
            The HTTP response.

        Raises:
            RuntimeError: If the harness was quarantined after cleanup failed.
        """
        if self._contaminated:
            raise RuntimeError(
                "API harness cannot be reused after a restoration failure"
            )
        return cast(
            requests.Response,
            case.call(
                base_url=self.server.base_url,
                session=self._session,
                headers={
                    "Authorization": f"Bearer {self.server.token}",
                    "X-Request-ID": f"fuzz-{uuid4()}",
                },
                timeout=REQUEST_TIMEOUT_SECONDS,
            ),
        )

    def seed_baseline(self) -> BaselineIds:
        """Create the reusable project, pipeline, snapshot, run, and tags.

        Returns:
            IDs of the newly seeded baseline resources.

        Raises:
            RuntimeError: If a baseline exists or a required response is invalid.
        """
        if self._baseline is not None:
            raise RuntimeError("API baseline has already been seeded")
        project = self.request_json(
            "POST", "/api/v1/projects", json={"name": "fuzz-api-project"}
        )
        stacks = self.request_json("GET", "/api/v1/stacks", params={"size": 1})
        if not stacks["items"]:
            raise RuntimeError("ZenML server did not create a default stack")
        pipeline = self.request_json(
            "POST",
            "/api/v1/pipelines",
            json={"name": "fuzz-api-pipeline", "project": project["id"]},
        )
        snapshot = self.request_json(
            "POST",
            "/api/v1/pipeline_snapshots",
            json={
                "project": project["id"],
                "pipeline": pipeline["id"],
                "stack": stacks["items"][0]["id"],
                "run_name_template": "fuzz-api-run",
                "pipeline_configuration": {"name": "fuzz-api-pipeline"},
                "step_configurations": {},
                "client_environment": {},
                "client_version": "fuzz-harness",
                "server_version": "fuzz-harness",
                "is_dynamic": False,
            },
        )
        run_result = self.request_json(
            "POST",
            "/api/v1/runs",
            json={
                "project": project["id"],
                "snapshot": snapshot["id"],
                "name": "fuzz-api-run",
                "status": "running",
            },
        )
        if not isinstance(run_result, list) or len(run_result) != 2:
            raise RuntimeError("Run creation returned an unexpected response")
        run = run_result[0]
        self.request_json(
            "PUT",
            f"/api/v1/runs/{run['id']}",
            json={"status": "completed"},
        )
        self._baseline = BaselineIds(
            project_id=project["id"],
            pipeline_id=pipeline["id"],
            snapshot_id=snapshot["id"],
            run_id=run["id"],
            tag_ids={},
        )
        return self.reset_tags()

    def openapi_schema(self) -> dict[str, Any]:
        """Fetch the live OpenAPI schema from the disposable server.

        Returns:
            Decoded OpenAPI document.

        Raises:
            RuntimeError: If the endpoint does not return a JSON object.
        """
        schema = self.request_json("GET", "/openapi.json")
        if not isinstance(schema, dict):
            raise RuntimeError("OpenAPI endpoint did not return an object")
        return schema

    def close(self) -> None:
        """Close the authenticated HTTP session."""
        self._session.close()

    def reset_tags(self) -> BaselineIds:
        """Delete all tags (bounded) and recreate the named baseline.

        Returns:
            Baseline resource IDs containing the new tag IDs.

        Raises:
            RuntimeError: If ownership fails, baseline is missing, or tags
                refuse to delete within ``MAX_TAG_RESET_ROUNDS``.
        """
        self.server.database.assert_owned()
        if self._baseline is None:
            raise RuntimeError("API baseline has not been seeded")
        for _ in range(MAX_TAG_RESET_ROUNDS):
            page = self.request_json(
                "GET", "/api/v1/tags", params={"page": 1, "size": 100}
            )
            items = page["items"]
            if not items:
                break
            for tag in items:
                self.request(
                    "DELETE",
                    f"/api/v1/tags/{tag['id']}",
                    expected_status=200,
                )
        else:
            remaining = self.request_json(
                "GET", "/api/v1/tags", params={"page": 1, "size": 100}
            )["items"]
            if remaining:
                stuck = [f"{t.get('name')} ({t.get('id')})" for t in remaining]
                raise RuntimeError(
                    "Tag reset did not converge after "
                    f"{MAX_TAG_RESET_ROUNDS} rounds; remaining tags: {stuck}"
                )

        tag_ids = {}
        for logical_name, request_body in _BASELINE_TAGS.items():
            tag = self.request_json("POST", "/api/v1/tags", json=request_body)
            tag_ids[logical_name] = tag["id"]
        self._baseline = replace(self._baseline, tag_ids=tag_ids)
        self._tags_dirty = False
        return self._baseline

    @contextmanager
    def prepared_example(
        self, *, mutates: bool
    ) -> Generator[BaselineIds, None, None]:
        """Ensure a clean tag baseline before an example without double resets.

        Read-only requests skip resetting when the baseline is already clean,
        cutting ~12 HTTP requests of overhead per read example. Any mutating
        request marks tags dirty so the next example resets once beforehand.

        Args:
            mutates: Whether the upcoming request may modify server state.

        Yields:
            Current clean baseline IDs.

        Raises:
            RuntimeError: If baseline restoration fails.
        """
        if self._baseline is None:
            raise RuntimeError("API baseline has not been seeded")
        try:
            if self._tags_dirty or not self._baseline.tag_ids:
                baseline = self.reset_tags()
            else:
                baseline = self._baseline
        except BaseException:
            self._contaminated = True
            raise

        if mutates:
            self._tags_dirty = True
        yield baseline

    def _url(self, path: str) -> str:
        """Build a URL constrained to the disposable server."""
        if not path.startswith("/"):
            raise ValueError("API request paths must start with '/'")
        return f"{self.server.base_url}{path}"
