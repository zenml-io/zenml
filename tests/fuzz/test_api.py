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
from pathlib import Path
from typing import Any, Generator, Mapping

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from requests import Response
from schemathesis import GenerationMode
from schemathesis.checks import not_a_server_error
from schemathesis.schemas import APIOperation
from schemathesis.specs.openapi.checks import (
    content_type_conformance,
    response_headers_conformance,
    response_schema_conformance,
)
from tests.fuzz.api_fixtures import ApiHarness, BaselineIds
from tests.fuzz.api_server import running_api_server
from tests.fuzz.api_strategies import (
    API_ALLOWLIST,
    CoverageMode,
    CoverageTracker,
    EvidenceRecorder,
    is_known_malformed_json_422,
    load_allowed_operations,
    semantic_case,
    substitute_fixture_ids,
)

_RESPONSE_CHECKS = [
    not_a_server_error,
    content_type_conformance,
    response_headers_conformance,
    response_schema_conformance,
]


@dataclass
class ApiRuntime:
    """Live resources shared by one isolated API test process."""

    harness: ApiHarness
    operations: Mapping[str, APIOperation[Any, Any, Any, Any]]
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
        try:
            harness.seed_baseline()
            operations = load_allowed_operations(harness.openapi_schema())
            yield ApiRuntime(
                harness=harness,
                operations=operations,
                coverage=CoverageTracker(),
                evidence=EvidenceRecorder(output_directory),
            )
        finally:
            harness.close()


def _evidence(
    operation_id: str,
    mode: CoverageMode,
    case: Any,
    response: Response | None = None,
    error: BaseException | None = None,
) -> dict[str, Any]:
    """Build a bounded request/response record safe for JSON serialization."""
    record: dict[str, Any] = {
        "operation_id": operation_id,
        "mode": mode,
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
    if error is not None:
        record["error"] = repr(error)
    return record


@contextmanager
def _executed_case(
    runtime: ApiRuntime, operation_id: str, mode: CoverageMode, case: Any
) -> Generator[Response, None, None]:
    """Execute, validate, count, and retain evidence for one isolated case."""
    response = None
    try:
        response = runtime.harness.call_case(case)
        runtime.coverage.record(operation_id, mode, response.status_code)
        runtime.evidence.write_coverage(runtime.coverage)
        runtime.evidence.record_case(
            _evidence(operation_id, mode, case, response=response)
        )
        assert response.status_code < 500, (
            f"{operation_id} returned unexpected {response.status_code}: "
            f"{response.text[:1000]}"
        )
        content_type = response.headers.get("content-type", "")
        if isinstance(content_type, list):
            content_type = content_type[0] if content_type else ""
        payload = None
        if content_type.startswith("application/json"):
            payload = response.json()
        # Positive schema generation intentionally includes values that ZenML
        # rejects with domain validators absent from OpenAPI (for example an
        # empty or UUID-like tag name). Validate every documented response but
        # do not turn those expected 4xx results into generator failures.
        checks = _RESPONSE_CHECKS
        # zenml-io/zenml#5269 tracks this exact malformed-JSON response.
        if is_known_malformed_json_422(
            operation_id, mode, response.status_code, payload
        ):
            checks = [
                check
                for check in checks
                if check is not response_schema_conformance
            ]
        case.validate_response(response, checks=checks)
        yield response
    except BaseException as error:
        if response is None:
            runtime.evidence.record_case(
                _evidence(operation_id, mode, case, error=error)
            )
        raise


def _assert_semantic_result(
    operation_id: str, response: Response, baseline: BaselineIds
) -> None:
    """Check that semantic requests reached their seeded target."""
    payload = response.json()
    if operation_id == "list_tags_api_v1_tags_get":
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
    api_runtime: ApiRuntime, spec: Any
) -> None:
    """Every allowlisted operation has an authenticated successful request."""
    with api_runtime.harness.isolated_example() as baseline:
        operation = api_runtime.operations[spec.operation_id]
        case = semantic_case(operation, spec.operation_id, baseline)
        with _executed_case(
            api_runtime, spec.operation_id, "semantic", case
        ) as response:
            assert 200 <= response.status_code < 300
            _assert_semantic_result(spec.operation_id, response, baseline)


@pytest.mark.parametrize(
    "spec", API_ALLOWLIST, ids=lambda spec: spec.operation_id
)
@settings(
    max_examples=1,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(data=st.data())
def test_schema_generated_positive_requests(
    api_runtime: ApiRuntime, spec: Any, data: st.DataObject
) -> None:
    """Every operation gets a schema-positive generated request."""
    case = data.draw(
        api_runtime.operations[spec.operation_id].as_strategy(
            generation_mode=GenerationMode.POSITIVE
        ),
        label=f"positive {spec.operation_id}",
    )
    with api_runtime.harness.isolated_example() as baseline:
        substitute_fixture_ids(case, baseline)
        with _executed_case(api_runtime, spec.operation_id, "positive", case):
            pass


@pytest.mark.parametrize(
    "spec", API_ALLOWLIST, ids=lambda spec: spec.operation_id
)
@settings(
    max_examples=1,
    suppress_health_check=[
        HealthCheck.function_scoped_fixture,
        HealthCheck.filter_too_much,
    ],
)
@given(data=st.data())
def test_schema_generated_negative_requests(
    api_runtime: ApiRuntime, spec: Any, data: st.DataObject
) -> None:
    """Every operation gets a schema-negative generated request."""
    case = data.draw(
        api_runtime.operations[spec.operation_id].as_strategy(
            generation_mode=GenerationMode.NEGATIVE
        ),
        label=f"negative {spec.operation_id}",
    )
    with api_runtime.harness.isolated_example():
        with _executed_case(api_runtime, spec.operation_id, "negative", case):
            pass


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
    with api_runtime.harness.isolated_example():
        case = operation.Case(**case_kwargs)
        with _executed_case(
            api_runtime, operation_id, "negative", case
        ) as response:
            assert 400 <= response.status_code < 500


def test_unsupported_filter_is_ignored_without_server_error(
    api_runtime: ApiRuntime,
) -> None:
    """An extra query filter follows FastAPI's intentional ignore behavior."""
    operation_id = "list_tags_api_v1_tags_get"
    operation = api_runtime.operations[operation_id]
    with api_runtime.harness.isolated_example():
        case = operation.Case(query={"unsupported_filter": "value"})
        with _executed_case(
            api_runtime, operation_id, "negative", case
        ) as response:
            assert response.status_code == 200


def test_explicit_null_tag_update_is_a_noop(api_runtime: ApiRuntime) -> None:
    """Nullable update fields do not crash or clear stored tag values."""
    operation_id = "update_tag_api_v1_tags__tag_id__put"
    operation = api_runtime.operations[operation_id]
    with api_runtime.harness.isolated_example() as baseline:
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


@settings(
    suppress_health_check=[
        HealthCheck.function_scoped_fixture,
        HealthCheck.filter_too_much,
    ]
)
@given(
    operation_index=st.integers(min_value=0, max_value=len(API_ALLOWLIST) - 1),
    generation_mode=st.sampled_from(
        [GenerationMode.POSITIVE, GenerationMode.NEGATIVE]
    ),
    data=st.data(),
)
def test_generated_requests_explore_the_allowlist(
    api_runtime: ApiRuntime,
    operation_index: int,
    generation_mode: GenerationMode,
    data: st.DataObject,
) -> None:
    """The selected profile explores additional bounded generated requests."""
    spec = API_ALLOWLIST[operation_index]
    case = data.draw(
        api_runtime.operations[spec.operation_id].as_strategy(
            generation_mode=generation_mode
        ),
        label=f"explore {spec.operation_id}",
    )
    mode: CoverageMode = (
        "positive"
        if generation_mode is GenerationMode.POSITIVE
        else "negative"
    )
    with api_runtime.harness.isolated_example() as baseline:
        if generation_mode is GenerationMode.POSITIVE:
            substitute_fixture_ids(case, baseline)
        with _executed_case(api_runtime, spec.operation_id, mode, case):
            pass


def test_api_coverage_qualifies(api_runtime: ApiRuntime) -> None:
    """No missing operation or zero-case generation can pass the API job."""
    api_runtime.coverage.qualify()
    api_runtime.evidence.write_coverage(api_runtime.coverage)
