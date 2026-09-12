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
from typing import Any, Callable, Generator, Mapping, Optional, TypeVar

import requests
from tests.fuzz.api_server import REQUEST_TIMEOUT_SECONDS, RunningApiServer

_T = TypeVar("_T")
_BASELINE_TAGS = {
    "primary": {"name": "fuzz-primary", "color": "grey"},
    "secondary": {"name": "fuzz-secondary", "color": "blue"},
}


class ApiCleanupError(RuntimeError):
    """Error that retains both an example failure and restoration failure."""

    def __init__(
        self,
        original_error: Optional[BaseException],
        cleanup_error: BaseException,
    ) -> None:
        """Initialize the combined failure.

        Args:
            original_error: Error raised by the generated example, if any.
            cleanup_error: Error raised while restoring the baseline.
        """
        self.original_error = original_error
        self.cleanup_error = cleanup_error
        super().__init__(
            f"API fixture restoration failed: {cleanup_error}; original error: "
            f"{original_error!r}"
        )


@contextmanager
def restore_around_example(
    reset: Callable[[], _T],
) -> Generator[_T, None, None]:
    """Restore a baseline before and after one generated example.

    Args:
        reset: Callable that safely restores and returns the baseline.

    Yields:
        The baseline created before the example.

    Raises:
        ApiCleanupError: If final restoration fails, retaining any example
            failure on the exception.
        BaseException: Re-raises the example failure after successful cleanup.
    """
    try:
        baseline = reset()
    except BaseException as cleanup_error:
        raise ApiCleanupError(None, cleanup_error) from cleanup_error

    try:
        yield baseline
    except BaseException as original_error:
        try:
            reset()
        except BaseException as cleanup_error:
            raise ApiCleanupError(
                original_error, cleanup_error
            ) from original_error
        raise
    else:
        try:
            reset()
        except BaseException as cleanup_error:
            raise ApiCleanupError(None, cleanup_error) from cleanup_error


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
        self._contaminated = False

    def anonymous_request(
        self, method: str, path: str, **kwargs: Any
    ) -> requests.Response:
        """Send an unauthenticated request to the disposable server.

        Args:
            method: HTTP method.
            path: Absolute API path relative to the disposable server.
            **kwargs: Additional arguments passed to ``requests.request``.

        Returns:
            The HTTP response.
        """
        return requests.request(
            method,
            self._url(path),
            timeout=REQUEST_TIMEOUT_SECONDS,
            **kwargs,
        )

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
            **kwargs: Additional arguments passed to the session request.

        Returns:
            The HTTP response.

        Raises:
            RuntimeError: If the harness is contaminated or the response status
                differs from ``expected_status``.
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
            **kwargs: Additional arguments passed to the session request.

        Returns:
            The decoded JSON response.

        """
        response = self.request(
            method, path, expected_status=expected_status, **kwargs
        )
        return response.json()

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
            The decoded OpenAPI schema.

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
        """Delete all tags and recreate the named baseline.

        Returns:
            Baseline resource IDs containing the new tag IDs.

        Raises:
            RuntimeError: If ownership cannot be proven or no baseline exists.
        """
        self.server.database.assert_owned()
        if self._baseline is None:
            raise RuntimeError("API baseline has not been seeded")
        while True:
            page = self.request_json(
                "GET", "/api/v1/tags", params={"page": 1, "size": 100}
            )
            if not page["items"]:
                break
            for tag in page["items"]:
                self.request(
                    "DELETE",
                    f"/api/v1/tags/{tag['id']}",
                    expected_status=200,
                )

        tag_ids = {}
        for logical_name, request_body in _BASELINE_TAGS.items():
            tag = self.request_json("POST", "/api/v1/tags", json=request_body)
            tag_ids[logical_name] = tag["id"]
        self._baseline = replace(self._baseline, tag_ids=tag_ids)
        return self._baseline

    @contextmanager
    def isolated_example(self) -> Generator[BaselineIds, None, None]:
        """Restore tags around one generated example and quarantine failures.

        Yields:
            Baseline IDs produced by the pre-example restoration.

        Raises:
            ApiCleanupError: If either restoration fails.
        """
        try:
            with restore_around_example(self.reset_tags) as baseline:
                yield baseline
        except ApiCleanupError:
            self._contaminated = True
            raise

    def current_baseline(self) -> BaselineIds:
        """Return the current baseline after verifying its logical tag names.

        Returns:
            Baseline IDs resolved from the current tag state.

        Raises:
            RuntimeError: If the baseline is absent or its tags do not match.
        """
        if self._baseline is None:
            raise RuntimeError("API baseline has not been seeded")
        tags = self._all_tags()
        ids_by_name = {tag["name"]: tag["id"] for tag in tags}
        expected_names = {tag["name"] for tag in _BASELINE_TAGS.values()}
        if set(ids_by_name) != expected_names:
            raise RuntimeError("API tags do not match the expected baseline")
        tag_ids = {
            logical_name: ids_by_name[tag["name"]]
            for logical_name, tag in _BASELINE_TAGS.items()
        }
        return replace(self._baseline, tag_ids=tag_ids)

    def tag_names(self) -> set[str]:
        """Return all tag names in the disposable database.

        Returns:
            Names of every stored tag.
        """
        return {tag["name"] for tag in self._all_tags()}

    def list_count(self, path: str) -> int:
        """Return the total reported by a list endpoint.

        Args:
            path: Absolute API path of the list endpoint.

        Returns:
            Total number of resources reported by the endpoint.

        Raises:
            RuntimeError: If project context is unavailable or the response is
                not paginated.
        """
        params: dict[str, int | str] = {"size": 1}
        if path in {"/api/v1/pipelines", "/api/v1/runs"}:
            if self._baseline is None:
                raise RuntimeError("API baseline has not been seeded")
            params["project"] = self._baseline.project_id
        page = self.request_json("GET", path, params=params)
        total = page.get("total")
        if not isinstance(total, int):
            raise RuntimeError(f"{path} did not return a paginated response")
        return total

    def _all_tags(self) -> list[dict[str, Any]]:
        """Fetch every tag page from the disposable server.

        Returns:
            Decoded tag objects from all pages.
        """
        tags: list[dict[str, Any]] = []
        page_number = 1
        while True:
            page = self.request_json(
                "GET",
                "/api/v1/tags",
                params={"page": page_number, "size": 100},
            )
            tags.extend(page["items"])
            if page_number >= page["total_pages"]:
                return tags
            page_number += 1

    def _url(self, path: str) -> str:
        """Build a URL constrained to the disposable server.

        Args:
            path: Absolute API path relative to the disposable server.

        Returns:
            Full request URL.

        Raises:
            ValueError: If ``path`` is not absolute.
        """
        if not path.startswith("/"):
            raise ValueError("API request paths must start with '/'")
        return f"{self.server.base_url}{path}"
