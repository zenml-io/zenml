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
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from zenml.evaluators.baseline import BaselineSpec, resolve_baseline
from zenml.evaluators.result import (
    EvaluationMode,
    EvaluationResult,
)


def _result(suite: str, mode: EvaluationMode, agg: dict) -> EvaluationResult:
    return EvaluationResult(
        evaluator="stub",
        mode=mode,
        suite_name=suite,
        cases=[],
        aggregates=agg,
        metadata={},
    )


def test_resolve_baseline_explicit_artifact_id(monkeypatch):
    artifact_id = uuid4()
    fake_result = _result("s", EvaluationMode.RAG, {"f": 0.8})
    fake_client = MagicMock()
    fake_client.get_artifact_version.return_value = MagicMock(
        load=MagicMock(return_value=fake_result)
    )
    monkeypatch.setattr(
        "zenml.evaluators.baseline.Client", lambda: fake_client
    )

    out = resolve_baseline(
        BaselineSpec(strategy="explicit", artifact_id=artifact_id),
        suite_name="s",
        mode=EvaluationMode.RAG,
    )
    assert out is fake_result


def test_resolve_baseline_none_strategy():
    out = resolve_baseline(
        BaselineSpec(strategy="none"),
        suite_name="s",
        mode=EvaluationMode.RAG,
    )
    assert out is None


def test_resolve_baseline_model_registry_no_production_version(monkeypatch):
    fake_client = MagicMock()
    fake_client.get_active_stack.return_value.model_registry = None
    monkeypatch.setattr(
        "zenml.evaluators.baseline.Client", lambda: fake_client
    )

    out = resolve_baseline(
        BaselineSpec(strategy="model_registry"),
        suite_name="s",
        mode=EvaluationMode.RAG,
    )
    # No registry, no production version -> graceful None.
    assert out is None


def test_resolve_baseline_explicit_requires_id():
    with pytest.raises(ValueError, match="artifact_id or run_id"):
        resolve_baseline(
            BaselineSpec(strategy="explicit"),
            suite_name="s",
            mode=EvaluationMode.RAG,
        )


def test_resolve_baseline_model_registry_with_production(monkeypatch):
    fake_result = _result("s", EvaluationMode.RAG, {"f": 0.85})
    fake_client = MagicMock()

    fake_registry = MagicMock()
    version_id = uuid4()
    fake_version = MagicMock()
    fake_version.id = version_id
    fake_registry.get_latest_model_version.return_value = fake_version

    fake_artifact = MagicMock()
    fake_artifact.load.return_value = fake_result

    fake_client.get_active_stack.return_value.model_registry = fake_registry
    fake_client.list_artifact_versions.return_value = [fake_artifact]

    monkeypatch.setattr(
        "zenml.evaluators.baseline.Client", lambda: fake_client
    )

    out = resolve_baseline(
        BaselineSpec(strategy="model_registry", model_name="my-model"),
        suite_name="s",
        mode=EvaluationMode.RAG,
    )
    assert out == fake_result
    fake_registry.get_latest_model_version.assert_called_once()
    fake_client.list_artifact_versions.assert_called_once_with(
        model_version_id=version_id
    )


def test_resolve_baseline_filters_by_suite_and_mode(monkeypatch):
    """Test that resolve_baseline filters artifacts by suite_name and mode."""
    matching_result = _result("s", EvaluationMode.RAG, {"f": 0.85})
    non_matching_result_wrong_suite = _result(
        "x", EvaluationMode.RAG, {"f": 0.75}
    )

    fake_client = MagicMock()
    fake_registry = MagicMock()
    version_id = uuid4()
    fake_version = MagicMock()
    fake_version.id = version_id
    fake_registry.get_latest_model_version.return_value = fake_version

    # Two artifacts: one matching suite_name/mode, one not (wrong suite name).
    matching_artifact = MagicMock()
    matching_artifact.load.return_value = matching_result
    non_matching_artifact = MagicMock()
    non_matching_artifact.load.return_value = non_matching_result_wrong_suite

    fake_client.get_active_stack.return_value.model_registry = fake_registry
    fake_client.list_artifact_versions.return_value = [
        non_matching_artifact,
        matching_artifact,
    ]

    monkeypatch.setattr(
        "zenml.evaluators.baseline.Client", lambda: fake_client
    )

    out = resolve_baseline(
        BaselineSpec(strategy="model_registry", model_name="my-model"),
        suite_name="s",
        mode=EvaluationMode.RAG,
    )
    # Should return the matching artifact (last one that matches).
    assert out == matching_result
