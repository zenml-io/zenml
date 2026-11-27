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
"""Bounded operation selection, filters, and failure evidence for API fuzzing."""

import json
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    Literal,
    Mapping,
    MutableMapping,
    Optional,
    Set,
)

import requests
import schemathesis
from schemathesis.schemas import APIOperation
from tests.fuzz.api_fixtures import BaselineIds

CoverageMode = Literal["semantic", "positive", "negative"]

# Reverse proxies commonly reject request lines over 8 KB, and Uvicorn refuses
# buffered request heads over 16 KB inconsistently depending on TCP framing,
# which makes Hypothesis abort with Flaky on replay (lesson from Kitaru #1539).
MAX_URL_BYTES = 8 * 1024


@dataclass(frozen=True)
class OperationSpec:
    """One explicitly allowed API operation."""

    operation_id: str
    method: str
    path: str

    @property
    def mutates(self) -> bool:
        """Return whether this HTTP method may mutate server state."""
        return self.method.upper() not in {"GET", "HEAD", "OPTIONS"}


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

_ALLOWLIST_IDS = frozenset(spec.operation_id for spec in API_ALLOWLIST)


def is_url_within_limit(case: Any) -> bool:
    """Return whether a generated case's encoded URL fits ``MAX_URL_BYTES``.

    Args:
        case: Generated Schemathesis case.

    Returns:
        ``True`` if the prepared HTTP URL is at or under ``MAX_URL_BYTES``.
    """
    kwargs = case.as_transport_kwargs(base_url="http://127.0.0.1")
    prepared = requests.Request(
        method=kwargs["method"],
        url=kwargs["url"],
        params=kwargs.get("params"),
    ).prepare()
    return len(prepared.url or "") <= MAX_URL_BYTES


def load_allowed_operations(
    raw_schema: Dict[str, Any],
) -> Dict[str, APIOperation[Any, Any, Any, Any]]:
    """Load and verify every operation in the fixed API allowlist.

    Args:
        raw_schema: OpenAPI document fetched from the running server.

    Returns:
        Operations keyed by operation ID.
    """
    schema = schemathesis.openapi.from_dict(raw_schema)
    return _verified_allowed_operations(schema)


def load_response_validation_operations(
    raw_schema: Dict[str, Any],
) -> tuple[Dict[str, APIOperation[Any, Any, Any, Any]], Set[str]]:
    """Load response-validation operations and record removed date-time fields.

    Args:
        raw_schema: Live OpenAPI document that remains unchanged.

    Returns:
        Tuple of ``(operations, datetime_field_names)``.
    """
    copied, datetime_fields = schema_without_datetime_formats(raw_schema)
    schema = schemathesis.openapi.from_dict(copied)
    return _verified_allowed_operations(schema), datetime_fields


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
) -> tuple[Dict[str, Any], Set[str]]:
    """Build a response-validation copy without ``format: date-time`` (#5270).

    Also returns the property names where ``format: date-time`` was stripped so
    responses can still be checked with ``datetime.fromisoformat`` instead of
    accepting arbitrary non-timestamp strings.

    Args:
        raw_schema: Live OpenAPI document that must remain unchanged.

    Returns:
        Tuple of ``(copied_schema, datetime_property_names)``.
    """
    schema = deepcopy(raw_schema)
    datetime_fields: Set[str] = set()

    def _strip(value: Any, property_name: Optional[str] = None) -> None:
        if isinstance(value, dict):
            if value.get("format") == "date-time":
                del value["format"]
                if property_name is not None:
                    datetime_fields.add(property_name)
            for key, item in value.items():
                if key == "properties" and isinstance(item, dict):
                    for prop_name, prop_schema in item.items():
                        _strip(prop_schema, prop_name)
                else:
                    _strip(item, property_name)
        elif isinstance(value, list):
            for item in value:
                _strip(item, property_name)

    _strip(schema)
    return schema, datetime_fields


def validate_naive_datetimes(payload: Any, datetime_fields: Set[str]) -> None:
    """Assert that response fields declared as ``date-time`` parse as ISO-8601.

    Args:
        payload: Decoded JSON response body.
        datetime_fields: Property names whose ``format: date-time`` was
            exempted for #5270.

    Raises:
        AssertionError: If a declared timestamp field contains non-ISO text.
    """
    if isinstance(payload, Mapping):
        for key, item in payload.items():
            if key in datetime_fields and isinstance(item, str):
                try:
                    datetime.fromisoformat(item.replace("Z", "+00:00"))
                except ValueError as error:
                    raise AssertionError(
                        f"Response field {key!r} is not a valid ISO-8601 "
                        f"timestamp: {item!r}"
                    ) from error
            else:
                validate_naive_datetimes(item, datetime_fields)
    elif isinstance(payload, list):
        for item in payload:
            validate_naive_datetimes(item, datetime_fields)


def is_known_request_validation_422(
    operation_id: str, status_code: int, payload: Any
) -> bool:
    """Return whether a 422 response matches ZenML's #5269 validation array.

    ZenML's global ``RequestValidationError`` handler returns
    ``["ValueError", "<text>"]`` instead of the documented ``ErrorModel`` for
    both negative and schema-positive requests (for example, UUID-like tag
    names rejected by ``TagRequest.validate_name_not_uuid``).

    Args:
        operation_id: Stable OpenAPI operation ID.
        status_code: HTTP response status.
        payload: Decoded JSON response.

    Returns:
        Whether the response matches the tracked #5269 validation shape.
    """
    return (
        operation_id in _ALLOWLIST_IDS
        and status_code == 422
        and isinstance(payload, list)
        and len(payload) == 2
        and payload[0] == "ValueError"
        and isinstance(payload[1], str)
    )


def semantic_case(
    operation: APIOperation[Any, Any, Any, Any],
    operation_id: str,
    baseline: BaselineIds,
) -> Any:
    """Build a request with valid domain values and current fixture IDs."""
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
    elif operation_id in {
        "list_pipelines_api_v1_pipelines_get",
        "list_runs_api_v1_runs_get",
    }:
        query = {"project": baseline.project_id, "page": 1, "size": 100}
    kwargs: Dict[str, Any] = {
        "path_parameters": path_parameters,
        "query": query,
    }
    if body is not None:
        kwargs.update(body=body, media_type=media_type)
    return operation.Case(**kwargs)


def substitute_fixture_ids(case: Any, baseline: BaselineIds) -> Any:
    """Replace generated resource IDs with IDs from the current baseline."""
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
    """Execution counters for one allowlisted operation."""

    semantic: int = 0
    positive: int = 0
    negative: int = 0
    successful_2xx: int = 0


@dataclass
class CoverageTracker:
    """Accumulate and qualify validated API operation coverage."""

    counts: MutableMapping[str, OperationCoverage] = field(
        default_factory=dict
    )

    def record(
        self, operation_id: str, mode: CoverageMode, status_code: int
    ) -> None:
        """Record one validated request outcome."""
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
        """Require semantic, positive, negative, and 2xx coverage per route."""
        failures = []
        for spec in expected:
            coverage = self.counts.get(spec.operation_id, OperationCoverage())
            missing = [
                name
                for name in (
                    "semantic",
                    "positive",
                    "negative",
                    "successful_2xx",
                )
                if getattr(coverage, name) == 0
            ]
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
    """Recursively redact credentials while keeping request identifiers."""
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
    """Write sanitized failing cases and final coverage counters."""

    def __init__(self, output_directory: Path) -> None:
        """Create the recorder for one run directory."""
        output_directory.mkdir(parents=True, exist_ok=True)
        self._failures_path = output_directory / "api-failures.jsonl"
        self._coverage_path = output_directory / "api-coverage.json"

    def record_failure(self, evidence: Mapping[str, Any]) -> None:
        """Append one sanitized failing request/response record."""
        with self._failures_path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(redact(evidence), sort_keys=True) + "\n")

    def write_coverage(self, tracker: CoverageTracker) -> None:
        """Atomically write final operation coverage counters."""
        temporary = self._coverage_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(tracker.as_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self._coverage_path)
