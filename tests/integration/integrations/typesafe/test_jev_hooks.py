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
"""Tests for the TypeSafe Jev hooks."""

import json
from typing import Any, Dict, List, Mapping

import pytest

pytest.importorskip("typesafe_sdk")

import httpx2  # noqa: E402
from typesafe_sdk import (  # noqa: E402
    Question,
    SystemOneResponse,
    TypeSafeRateLimitError,
)

from zenml import pipeline, step  # noqa: E402
from zenml.client import Client  # noqa: E402
from zenml.integrations.typesafe.hooks import (  # noqa: E402
    jev_classify_and_log,
    jev_failure_triage_hook,
    jev_hooks,
    jev_run_summary_hook,
)

ANSWERS: Dict[str, Dict[str, Any]] = {
    "failure_category": {
        "type": "choice",
        "choice": "infrastructure",
        "confidence": 0.8,
        "probabilities": {"infrastructure": 0.8, "code": 0.2},
    },
    "retry_likely_to_help": {"type": "noul", "noul": 0.9},
    "needs_attention": {"type": "noul", "noul": 0.1},
    "anomaly": {
        "type": "score",
        "score": 0.3,
        "confidence": 0.7,
        "legend": {"0": "normal", "1": "odd", "2": "very odd"},
        "probabilities": {"0": 0.75, "1": 0.2, "2": 0.05},
    },
}


class FakeTypeSafeClient:
    """Stands in for `TypeSafeClient` and answers every question."""

    calls: List[Dict[str, Any]] = []
    error: Exception | None = None

    def __init__(self, **kwargs: Any) -> None:
        pass

    def __enter__(self) -> "FakeTypeSafeClient":
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def system_one(
        self, state: Any, questions: Mapping[str, Question], **kwargs: Any
    ) -> SystemOneResponse:
        FakeTypeSafeClient.calls.append(
            {"state": state, "questions": dict(questions)}
        )
        if FakeTypeSafeClient.error:
            raise FakeTypeSafeClient.error
        body = {
            "model": "jev-test",
            "usage": {"input_tokens": 10, "output_tokens": 1},
            "answers": {name: ANSWERS[name] for name in questions},
        }
        # The SDK validates answers strictly from JSON, which is also how it
        # coerces score levels to integers.
        return SystemOneResponse.model_validate_json(json.dumps(body))


@pytest.fixture
def fake_jev(monkeypatch: pytest.MonkeyPatch) -> type:
    FakeTypeSafeClient.calls = []
    FakeTypeSafeClient.error = None
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.setattr(jev_hooks, "TypeSafeClient", FakeTypeSafeClient)
    return FakeTypeSafeClient


@step(on_failure=jev_failure_triage_hook)
def flaky_step() -> None:
    raise ConnectionResetError("Connection reset by peer")


@pipeline(enable_cache=False)
def static_failing_pipeline() -> None:
    flaky_step()


@step
def ok_step() -> int:
    return 1


@pipeline(dynamic=True, enable_cache=False, on_end=jev_run_summary_hook)
def dynamic_pipeline() -> None:
    ok_step()


@pipeline(dynamic=True, enable_cache=False, on_failure=jev_failure_triage_hook)
def dynamic_failing_pipeline() -> None:
    raise ValueError("bad input data")


def test_response_to_metadata_flattens_every_answer_type() -> None:
    response = SystemOneResponse.model_validate_json(
        json.dumps({"model": "jev-test", "usage": {}, "answers": ANSWERS})
    )

    metadata = jev_hooks.response_to_metadata(response, prefix="jev")

    assert metadata["jev.model"] == "jev-test"
    assert metadata["jev.failure_category"] == "infrastructure"
    assert metadata["jev.failure_category.confidence"] == 0.8
    assert metadata["jev.retry_likely_to_help"] == 0.9
    assert metadata["jev.anomaly"] == 0.3
    assert metadata["jev.anomaly.probabilities"] == {
        "0": 0.75,
        "1": 0.2,
        "2": 0.05,
    }
    assert metadata["jev.anomaly.legend"]["2"] == "very odd"


def test_failure_hook_logs_triage_on_failed_step(
    clean_client: Client, fake_jev: type
) -> None:
    with pytest.raises(RuntimeError):
        static_failing_pipeline()

    [call] = fake_jev.calls
    assert call["state"]["step_name"] == "flaky_step"
    assert (
        "ConnectionResetError: Connection reset by peer"
        in call["state"]["traceback"]
    )

    run = clean_client.get_pipeline("static_failing_pipeline").last_run
    metadata = run.steps["flaky_step"].run_metadata
    assert metadata["jev.failure_category"] == "infrastructure"
    assert metadata["jev.retry_likely_to_help"] == 0.9

    [matching_step] = clean_client.list_run_steps(
        run_metadata="jev.failure_category:infrastructure"
    ).items
    assert matching_step.pipeline_run_id == run.id


def test_failure_hook_logs_triage_on_dynamic_run(
    clean_client: Client, fake_jev: type
) -> None:
    with pytest.raises(ValueError):
        dynamic_failing_pipeline()

    [call] = fake_jev.calls
    assert "ValueError: bad input data" in call["state"]["traceback"]
    assert "step_name" not in call["state"]

    run = clean_client.get_pipeline("dynamic_failing_pipeline").last_run
    assert run.run_metadata["jev.failure_category"] == "infrastructure"


def test_run_summary_hook_logs_assessment_on_dynamic_run(
    clean_client: Client, fake_jev: type
) -> None:
    dynamic_pipeline()
    dynamic_pipeline()

    last_call = fake_jev.calls[-1]
    state = last_call["state"]
    assert state["pipeline_name"] == "dynamic_pipeline"
    assert state["status"] == "completed"
    assert [s["name"] for s in state["steps"]] == ["ok_step"]
    [previous_run] = state["recent_runs"]
    assert previous_run["status"] == "completed"
    assert previous_run["step_count"] == 1
    assert previous_run["duration_seconds"] is not None

    run = clean_client.get_pipeline("dynamic_pipeline").last_run
    assert run.run_metadata["jev.needs_attention"] == 0.1
    assert run.run_metadata["jev.anomaly"] == 0.3

    calm_runs = clean_client.list_pipeline_runs(
        run_metadata="jev.needs_attention:lt:0.5"
    )
    assert calm_runs.total == 2


def test_run_summary_hook_skips_outside_dynamic_run(fake_jev: type) -> None:
    jev_run_summary_hook()

    assert fake_jev.calls == []


def test_classify_skips_without_api_key(
    fake_jev: type, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(jev_hooks, "_get_api_key", lambda: None)

    assert jev_classify_and_log("text", questions={}) is None
    assert fake_jev.calls == []


def test_classify_swallows_api_errors(fake_jev: type) -> None:
    fake_jev.error = TypeSafeRateLimitError(429, None, httpx2.Headers())

    assert (
        jev_classify_and_log("text", questions=jev_hooks.RUN_SUMMARY_QUESTIONS)
        is None
    )
    assert len(fake_jev.calls) == 1
