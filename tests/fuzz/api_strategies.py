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
"""Bounded operation selection and evidence for API fuzz tests."""

import json
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    Literal,
    Mapping,
    MutableMapping,
    Optional,
)

import schemathesis
from schemathesis.schemas import APIOperation
from tests.fuzz.api_fixtures import BaselineIds

CoverageMode = Literal["semantic", "positive", "negative"]


@dataclass(frozen=True)
class OperationSpec:
    """One explicitly allowed API operation."""

    operation_id: str
    method: str
    path: str


API_ALLOWLIST = (
    OperationSpec("create_tag_api_v1_tags_post", "POST", "/api/v1/tags"),
    OperationSpec("list_tags_api_v1_tags_get", "GET", "/api/v1/tags"),
    OperationSpec(
        "get_tag_api_v1_tags__tag_id__get",
        "GET",
        "/api/v1/tags/{tag_id}",
    ),
    OperationSpec(
        "update_tag_api_v1_tags__tag_id__put",
        "PUT",
        "/api/v1/tags/{tag_id}",
    ),
    OperationSpec(
        "delete_tag_api_v1_tags__tag_id__delete",
        "DELETE",
        "/api/v1/tags/{tag_id}",
    ),
    OperationSpec(
        "list_projects_api_v1_projects_get", "GET", "/api/v1/projects"
    ),
    OperationSpec(
        "list_pipelines_api_v1_pipelines_get", "GET", "/api/v1/pipelines"
    ),
    OperationSpec("list_runs_api_v1_runs_get", "GET", "/api/v1/runs"),
)


def load_allowed_operations(
    raw_schema: Dict[str, Any],
) -> Dict[str, APIOperation[Any, Any, Any, Any]]:
    """Load and verify every operation in the fixed API allowlist.

    Args:
        raw_schema: OpenAPI document fetched from the running server.

    Returns:
        Operations keyed by operation ID.

    Raises:
        RuntimeError: If an operation is absent or has a stale operation ID.
    """
    schema = schemathesis.openapi.from_dict(raw_schema)
    return _verified_allowed_operations(schema)


def load_response_validation_operations(
    raw_schema: Dict[str, Any],
) -> Dict[str, APIOperation[Any, Any, Any, Any]]:
    """Load operations from the response-validation schema.

    This separate schema is used only to validate responses. Request generation
    continues to use the unmodified live schema, including all date-time
    formats.

    Args:
        raw_schema: OpenAPI document fetched from the running server.

    Returns:
        Response-validation operations keyed by operation ID.

    Raises:
        RuntimeError: If an operation is absent or has a stale operation ID.
    """
    schema = schemathesis.openapi.from_dict(
        schema_without_datetime_formats(raw_schema)
    )
    return _verified_allowed_operations(schema)


def _verified_allowed_operations(
    schema: Any,
) -> Dict[str, APIOperation[Any, Any, Any, Any]]:
    """Return the fixed allowlist after verifying the loaded schema."""
    operations: Dict[str, APIOperation[Any, Any, Any, Any]] = {}
    for spec in API_ALLOWLIST:
        try:
            operation = schema[spec.path][spec.method]
        except (KeyError, LookupError) as error:
            raise RuntimeError(
                f"Allowlisted operation is missing: {spec.method} {spec.path}"
            ) from error
        live_operation_id = operation.definition.raw.get("operationId")
        if live_operation_id != spec.operation_id:
            raise RuntimeError(
                f"Stale operation ID for {spec.method} {spec.path}: "
                f"expected {spec.operation_id!r}, got {live_operation_id!r}"
            )
        operations[spec.operation_id] = operation
    return operations


def schema_without_datetime_formats(
    raw_schema: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the dedicated response-validation schema for issue #5270.

    ZenML emits timezone-less timestamps for fields documented as RFC 3339
    date-times. This copy is loaded only for response validation. Request
    generation uses the original schema and therefore retains every format.
    The copied schema retains every non-date-time format, including UUIDs and
    URIs.

    Args:
        raw_schema: Live OpenAPI document that must remain unchanged.

    Returns:
        A copied response-validation schema without ``format: date-time``.
    """
    schema = deepcopy(raw_schema)

    def remove_datetime_format(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("format") == "date-time":
                del value["format"]
            for item in value.values():
                remove_datetime_format(item)
        elif isinstance(value, list):
            for item in value:
                remove_datetime_format(item)

    remove_datetime_format(schema)
    return schema


def is_known_malformed_json_422(
    operation_id: str, mode: CoverageMode, status_code: int, payload: Any
) -> bool:
    """Return whether a response matches the exact issue #5269 exclusion.

    Args:
        operation_id: Stable OpenAPI operation ID.
        mode: Generated-case classification.
        status_code: HTTP response status.
        payload: Decoded JSON response.

    Returns:
        Whether the response is the known allowlisted validation array.
    """
    return (
        operation_id in {spec.operation_id for spec in API_ALLOWLIST}
        and mode == "negative"
        and status_code == 422
        and isinstance(payload, list)
        and len(payload) == 2
        and isinstance(payload[0], str)
        and payload[0] == "ValueError"
        and isinstance(payload[1], str)
    )


def semantic_case(
    operation: APIOperation[Any, Any, Any, Any],
    operation_id: str,
    baseline: BaselineIds,
) -> Any:
    """Build a request with valid domain values and current fixture IDs.

    Args:
        operation: Schemathesis operation used to construct the case.
        operation_id: Stable OpenAPI operation ID.
        baseline: IDs restored for this generated invocation.

    Returns:
        A Schemathesis case for the operation.
    """
    path_parameters: Optional[Dict[str, Any]] = None
    query: Optional[Dict[str, Any]] = None
    body: Any = None
    media_type: Optional[str] = None
    if "__tag_id__" in operation_id:
        path_parameters = {"tag_id": baseline.tag_ids["primary"]}
    if operation_id == "create_tag_api_v1_tags_post":
        body = {"name": "generated-smoke", "color": "green"}
        media_type = "application/json"
    elif operation_id == "update_tag_api_v1_tags__tag_id__put":
        body = {"name": "updated-smoke", "color": "blue"}
        media_type = "application/json"
    elif operation_id == "list_tags_api_v1_tags_get":
        query = {"page": 1, "size": 100}
    elif operation_id == "list_projects_api_v1_projects_get":
        query = {"id": baseline.project_id, "page": 1, "size": 100}
    elif operation_id == "list_pipelines_api_v1_pipelines_get":
        query = {
            "project": baseline.project_id,
            "page": 1,
            "size": 100,
        }
    elif operation_id == "list_runs_api_v1_runs_get":
        query = {
            "project": baseline.project_id,
            "page": 1,
            "size": 100,
        }
    kwargs: Dict[str, Any] = {
        "path_parameters": path_parameters,
        "query": query,
    }
    if body is not None:
        kwargs.update(body=body, media_type=media_type)
    return operation.Case(**kwargs)


def substitute_fixture_ids(case: Any, baseline: BaselineIds) -> Any:
    """Replace generated resource IDs with IDs from the current baseline.

    Args:
        case: Generated Schemathesis case.
        baseline: IDs restored immediately before the generated call.

    Returns:
        The mutated case.
    """
    if case.path_parameters and "tag_id" in case.path_parameters:
        case.path_parameters["tag_id"] = baseline.tag_ids["primary"]
    if case.query:
        if "project" in case.query:
            case.query["project"] = baseline.project_id
        if "pipeline" in case.query:
            case.query["pipeline"] = baseline.pipeline_id
        if "snapshot" in case.query:
            case.query["snapshot"] = baseline.snapshot_id
    return case


@dataclass
class OperationCoverage:
    """Execution counters for one operation."""

    semantic: int = 0
    positive: int = 0
    negative: int = 0
    successful_2xx: int = 0


@dataclass
class CoverageTracker:
    """Accumulate and qualify API operation coverage."""

    counts: MutableMapping[str, OperationCoverage] = field(
        default_factory=dict
    )

    def record(
        self, operation_id: str, mode: CoverageMode, status_code: int
    ) -> None:
        """Record one completed request.

        Args:
            operation_id: Stable OpenAPI operation ID.
            mode: ``semantic``, ``positive``, or ``negative``.
            status_code: HTTP response status.

        """
        coverage = self.counts.setdefault(operation_id, OperationCoverage())
        if mode == "semantic":
            coverage.semantic += 1
        elif mode == "positive":
            coverage.positive += 1
        else:
            coverage.negative += 1
        if 200 <= status_code < 300:
            coverage.successful_2xx += 1

    def qualify(
        self, expected: Iterable[OperationSpec] = API_ALLOWLIST
    ) -> None:
        """Require complete generated coverage and a success for every operation.

        Args:
            expected: Operations that must qualify.

        Raises:
            AssertionError: If any required counter is zero.
        """
        failures = []
        for spec in expected:
            coverage = self.counts.get(spec.operation_id, OperationCoverage())
            missing = [
                name
                for name in ("semantic", "positive", "negative")
                if getattr(coverage, name) == 0
            ]
            if coverage.successful_2xx == 0:
                missing.append("successful_2xx")
            if missing:
                failures.append(f"{spec.operation_id}: {', '.join(missing)}")
        assert not failures, "API coverage did not qualify: " + "; ".join(
            failures
        )

    def as_dict(self) -> Dict[str, Dict[str, int]]:
        """Return JSON-serializable operation counters."""
        return {
            operation_id: asdict(coverage)
            for operation_id, coverage in sorted(self.counts.items())
        }


_SECRET_KEYS = {
    "api-key",
    "authorization",
    "cookie",
    "password",
    "secret",
    "set-cookie",
    "token",
}


def redact(value: Any) -> Any:
    """Recursively redact credentials while retaining request identifiers.

    Args:
        value: Arbitrary evidence value.

    Returns:
        A recursively sanitized value.
    """
    if isinstance(value, Mapping):
        sanitized = {}
        for key, item in value.items():
            normalized = str(key).lower().replace("_", "-")
            sanitized[key] = (
                "[REDACTED]"
                if normalized in _SECRET_KEYS
                or normalized.endswith(("-password", "-secret", "-token"))
                else redact(item)
            )
        return sanitized
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    return value


class EvidenceRecorder:
    """Write sanitized request and coverage evidence for one fuzz batch."""

    def __init__(self, output_directory: Path) -> None:
        """Create the recorder.

        Args:
            output_directory: Owned directory for retained fuzz artifacts.
        """
        output_directory.mkdir(parents=True, exist_ok=True)
        self._cases_path = output_directory / "api-cases.jsonl"
        self._coverage_path = output_directory / "api-coverage.json"

    def record_case(self, evidence: Mapping[str, Any]) -> None:
        """Append one sanitized request and response record."""
        with self._cases_path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(redact(evidence), sort_keys=True) + "\n")

    def write_coverage(self, tracker: CoverageTracker) -> None:
        """Atomically write current operation counters."""
        temporary = self._coverage_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(tracker.as_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self._coverage_path)
