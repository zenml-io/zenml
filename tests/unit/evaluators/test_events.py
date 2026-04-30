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
"""Tests for evaluator event payload types."""

from uuid import uuid4

from zenml.evaluators.events import EvalRegressionEvent
from zenml.evaluators.result import EvaluationMode


def test_eval_regression_event_payload():
    e = EvalRegressionEvent(
        suite_name="rag_quality",
        mode=EvaluationMode.RAG,
        evaluator="openai",
        pipeline_run_id=uuid4(),
        artifact_id=uuid4(),
        aggregates={"faithfulness": 0.7},
        baseline_aggregates={"faithfulness": 0.85},
        regressed_metrics={"faithfulness": -0.15},
        model_version_id=None,
    )
    assert e.regressed_metrics["faithfulness"] == -0.15
    assert e.suite_name == "rag_quality"


def test_eval_regression_event_optional_model_version():
    e = EvalRegressionEvent(
        suite_name="x",
        mode=EvaluationMode.POINTWISE,
        evaluator="stub",
        pipeline_run_id=uuid4(),
        artifact_id=uuid4(),
        aggregates={},
        baseline_aggregates={},
        regressed_metrics={},
        # model_version_id omitted (defaults to None)
    )
    assert e.model_version_id is None
