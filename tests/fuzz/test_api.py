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
"""Bounded Schemathesis checks against an authenticated ZenML server."""

import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Generator, Mapping, Set, cast

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from requests import Response
from schemathesis import CheckFunction, GenerationMode
from schemathesis.checks import not_a_server_error
from schemathesis.schemas import APIOperation
from schemathesis.specs.openapi.checks import (
    content_type_conformance,
    response_headers_conformance,
    response_schema_conformance,
    status_code_conformance,
)
from tests.fuzz.api_fixtures import ApiHarness, BaselineIds
from tests.fuzz.api_server import running_api_server
from tests.fuzz.api_strategies import (
    API_ALLOWLIST,
    CoverageMode,
    CoverageTracker,
    EvidenceRecorder,
    OperationSpec,
    is_known_request_validation_422,
    is_url_within_limit,
    load_allowed_operations,
    load_response_validation_operations,
    semantic_case,
    substitute_fixture_ids,
    validate_naive_datetimes,
)

_NON_SCHEMA_CHECKS = cast(
    list[CheckFunction],
    [
        not_a_server_error,
        status_code_conformance,
        content_type_conformance,
        response_headers_conformance,
    ],
)


@dataclass
class ApiRuntime:
    """Live resources shared by one isolated API fuzz process."""

    harness: ApiHarness
    operations: Mapping[str, APIOperation[Any, Any, Any, Any]]
    response_validation_operations: Mapping[
        str, APIOperation[Any, Any, Any, Any]
    ]
    datetime_fields: Set[str]
    coverage: CoverageTracker
    evidence: EvidenceRecorder


@pytest.fixture(scope="module")
def api_runtime(
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[ApiRuntime, None, None]:
    """Start the disposable server and load its live OpenAPI contract."""
    backend = os.environ.get("ZENML_FUZZ_BACKEND", "sqlite")
    fallback_output = tmp_path_factory.mktemp("api-evidence")
    output_directory = Path(
        os.environ.get("ZENML_FUZZ_OUTPUT_DIR", fallback_output)
    )
    with running_api_server(
        backend=backend, output_directory=output_directory
    ) as server:
        harness = ApiHarness(server)
        coverage = CoverageTracker()
        evidence = EvidenceRecorder(output_directory)
        try:
            harness.seed_baseline()
            raw_schema = harness.openapi_schema()
            operations = load_allowed_operations(raw_schema)
            response_validation_operations, datetime_fields = (
                load_response_validation_operations(raw_schema)
            )
            yield ApiRuntime(
                harness=harness,
                operations=operations,
                response_validation_operations=response_validation_operations,
                datetime_fields=datetime_fields,
                coverage=coverage,
                evidence=evidence,
            )
        finally:
            evidence.write_coverage(coverage)
            harness.close()


def _failure_evidence(
    operation_id: str,
    mode: CoverageMode,
    case: Any,
    response: Response | None,
    error: BaseException,
) -> dict[str, Any]:
    """Build a bounded JSON-safe failure record for ``api-failures.jsonl``."""
    record: dict[str, Any] = {
        "operation_id": operation_id,
        "mode": mode,
        "error": repr(error),
        "request": {
            "method": case.method,
            "path": case.path,
            "path_parameters": repr(case.path_parameters),
            "query": repr(case.query),
            "headers": dict(case.headers or {}),
            "body": repr(case.body),
        },
    }
    if response is not None:
        record["request"].update(
            {
                "url": response.request.url,
                "headers": dict(response.request.headers),
                "request_id": response.request.headers.get("X-Request-ID"),
            }
        )
        record["response"] = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text[:2000],
        }
    return record


@contextmanager
def _executed_case(
    runtime: ApiRuntime, operation_id: str, mode: CoverageMode, case: Any
) -> Generator[Response, None, None]:
    """Execute and validate one case, recording coverage only after checks."""
    response: Response | None = None
    try:
        response = runtime.harness.call_case(case)
        if response.status_code >= 500:
            server_tail = runtime.harness.server.tail_log()
            raise AssertionError(
                f"{operation_id} returned {response.status_code}: "
                f"{response.text[:1000]}\n--- api-server.log tail ---\n"
                f"{server_tail}"
            )
        content_type = response.headers.get("content-type", "")
        if isinstance(content_type, list):
            content_type = content_type[0] if content_type else ""
        payload = None
        if content_type.lower().startswith("application/json"):
            payload = response.json()
        checks = (
            [
                check
                for check in _NON_SCHEMA_CHECKS
                if check is not status_code_conformance
            ]
            if response.status_code == 400
            and isinstance(payload, dict)
            and "detail" in payload
            else _NON_SCHEMA_CHECKS
        )
        case.validate_response(response, checks=checks)
        # zenml-io/zenml#5269 tracks the raw ["ValueError", "<text>"] 422 shape.
        if not is_known_request_validation_422(
            operation_id, response.status_code, payload
        ):
            validation_operation = runtime.response_validation_operations[
                operation_id
            ]
            validation_case = validation_operation.Case(
                path_parameters=case.path_parameters,
                headers=case.headers,
                cookies=case.cookies,
                query=case.query,
                body=case.body,
                media_type=case.media_type,
            )
            validation_case.validate_response(
                response,
                checks=[response_schema_conformance],
            )
            # zenml-io/zenml#5270 strips format: date-time for naive timestamps,
            # so still verify every declared date-time field parses as ISO-8601.
            if payload is not None:
                validate_naive_datetimes(payload, runtime.datetime_fields)
        runtime.coverage.record(operation_id, mode, response.status_code)
        yield response
    except BaseException as error:
        runtime.evidence.record_failure(
            _failure_evidence(operation_id, mode, case, response, error)
        )
        raise


def _assert_semantic_result(
    runtime: ApiRuntime,
    operation_id: str,
    response: Response,
    baseline: BaselineIds,
) -> None:
    """Verify semantic requests reached or persisted their expected state."""
    payload = response.json()
    if operation_id == "create_tag_api_v1_tags_post":
        created = runtime.harness.request_json(
            "GET", f"/api/v1/tags/{payload['id']}"
        )
        assert created["name"] == "generated-smoke"
        assert created["body"]["color"] == "green"
    elif operation_id == "update_tag_api_v1_tags__tag_id__put":
        updated = runtime.harness.request_json(
            "GET", f"/api/v1/tags/{baseline.tag_ids['primary']}"
        )
        assert updated["name"] == "updated-smoke"
        assert updated["body"]["color"] == "blue"
    elif operation_id == "delete_tag_api_v1_tags__tag_id__delete":
        deleted = runtime.harness.request(
            "GET", f"/api/v1/tags/{baseline.tag_ids['primary']}"
        )
        assert deleted.status_code == 404
    elif operation_id == "list_tags_api_v1_tags_get":
        assert set(baseline.tag_ids.values()).issubset(
            {item["id"] for item in payload["items"]}
        )
    elif operation_id == "get_tag_api_v1_tags__tag_id__get":
        assert payload["id"] == baseline.tag_ids["primary"]
    elif operation_id == "list_projects_api_v1_projects_get":
        assert baseline.project_id in {item["id"] for item in payload["items"]}
    elif operation_id == "list_pipelines_api_v1_pipelines_get":
        assert baseline.pipeline_id in {
            item["id"] for item in payload["items"]
        }
    elif operation_id == "list_runs_api_v1_runs_get":
        assert baseline.run_id in {item["id"] for item in payload["items"]}


@pytest.mark.parametrize(
    "spec", API_ALLOWLIST, ids=lambda spec: spec.operation_id
)
def test_semantically_valid_operation_succeeds(
    api_runtime: ApiRuntime, spec: OperationSpec
) -> None:
    """Every allowlisted operation succeeds and persists expected state."""
    with api_runtime.harness.prepared_example(mutates=spec.mutates) as base:
        operation = api_runtime.operations[spec.operation_id]
        case = semantic_case(operation, spec.operation_id, base)
        with _executed_case(
            api_runtime, spec.operation_id, "semantic", case
        ) as response:
            assert 200 <= response.status_code < 300
            _assert_semantic_result(
                api_runtime, spec.operation_id, response, base
            )


@pytest.mark.parametrize(
    ("operation_id", "case_kwargs"),
    [
        (
            "get_tag_api_v1_tags__tag_id__get",
            {"path_parameters": {"tag_id": "not-a-uuid"}},
        ),
        (
            "create_tag_api_v1_tags_post",
            {"body": {"name": ""}, "media_type": "application/json"},
        ),
        (
            "create_tag_api_v1_tags_post",
            {
                "body": {"name": "00000000-0000-0000-0000-000000000001"},
                "media_type": "application/json",
            },
        ),
        (
            "create_tag_api_v1_tags_post",
            {"body": {"name": "x" * 256}, "media_type": "application/json"},
        ),
        (
            "create_tag_api_v1_tags_post",
            {
                "body": {"name": "invalid-color", "color": "chartreuse"},
                "media_type": "application/json",
            },
        ),
        ("list_tags_api_v1_tags_get", {"query": {"page": 0}}),
    ],
)
def test_established_invalid_inputs_are_rejected(
    api_runtime: ApiRuntime,
    operation_id: str,
    case_kwargs: dict[str, Any],
) -> None:
    """Inputs rejected by ZenML's schema or validators return a 4xx."""
    operation = api_runtime.operations[operation_id]
    with api_runtime.harness.prepared_example(mutates=True):
        case = operation.Case(**case_kwargs)
        with _executed_case(
            api_runtime, operation_id, "negative", case
        ) as response:
            assert 400 <= response.status_code < 500


def test_explicit_null_tag_update_is_a_noop(api_runtime: ApiRuntime) -> None:
    """Nullable update fields do not crash or clear stored tag values."""
    operation_id = "update_tag_api_v1_tags__tag_id__put"
    operation = api_runtime.operations[operation_id]
    with api_runtime.harness.prepared_example(mutates=True) as baseline:
        case = operation.Case(
            path_parameters={"tag_id": baseline.tag_ids["primary"]},
            body={"name": None, "exclusive": None, "color": None},
            media_type="application/json",
        )
        with _executed_case(
            api_runtime, operation_id, "positive", case
        ) as response:
            assert response.status_code == 200
            payload = response.json()
            assert payload["name"] == "fuzz-primary"
            assert payload["body"]["color"] == "grey"
            assert payload["body"]["exclusive"] is False


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="zenml-io/zenml#5269: RequestValidationError returns a raw list instead of ErrorModel",
)
def test_known_issue_5269_validation_error_uses_error_model(
    api_runtime: ApiRuntime,
) -> None:
    """Canary for #5269: fails XPASS once 422 returns the documented object."""
    with api_runtime.harness.prepared_example(mutates=False):
        response = api_runtime.harness.request(
            "GET", "/api/v1/tags", params={"page": 0}
        )
        assert response.status_code == 422
        assert isinstance(response.json(), dict)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="zenml-io/zenml#5270: API timestamps omit UTC offset",
)
def test_known_issue_5270_timestamps_include_timezone(
    api_runtime: ApiRuntime,
) -> None:
    """Canary for #5270: fails XPASS once timestamps carry a timezone offset."""
    with api_runtime.harness.prepared_example(mutates=False) as baseline:
        tag = api_runtime.harness.request_json(
            "GET", f"/api/v1/tags/{baseline.tag_ids['primary']}"
        )
        parsed = datetime.fromisoformat(
            tag["body"]["created"].replace("Z", "+00:00")
        )
        assert parsed.tzinfo is not None


@pytest.mark.parametrize(
    "spec", API_ALLOWLIST, ids=lambda spec: spec.operation_id
)
@pytest.mark.parametrize(
    "generation_mode",
    [GenerationMode.POSITIVE, GenerationMode.NEGATIVE],
    ids=["positive", "negative"],
)
@settings(
    suppress_health_check=[
        HealthCheck.function_scoped_fixture,
        HealthCheck.filter_too_much,
    ]
)
@given(data=st.data())
def test_generated_requests_conform_to_api_contract(
    api_runtime: ApiRuntime,
    spec: OperationSpec,
    generation_mode: GenerationMode,
    data: st.DataObject,
) -> None:
    """Each allowlisted operation is independently fuzzed in both modes."""
    strategy = (
        api_runtime.operations[spec.operation_id]
        .as_strategy(generation_mode=generation_mode)
        .filter(is_url_within_limit)
    )
    case = data.draw(
        strategy, label=f"{generation_mode.value} {spec.operation_id}"
    )
    mode: CoverageMode = (
        "positive"
        if generation_mode is GenerationMode.POSITIVE
        else "negative"
    )
    with api_runtime.harness.prepared_example(mutates=spec.mutates) as base:
        if generation_mode is GenerationMode.POSITIVE:
            substitute_fixture_ids(case, base)
        with _executed_case(api_runtime, spec.operation_id, mode, case):
            pass


def test_api_coverage_qualifies(api_runtime: ApiRuntime) -> None:
    """Require validated semantic, positive, negative, and 2xx hits per route."""
    api_runtime.coverage.qualify()
    api_runtime.evidence.write_coverage(api_runtime.coverage)
