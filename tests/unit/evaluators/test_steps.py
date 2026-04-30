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
from unittest.mock import patch

import pytest

from zenml.evaluators.exceptions import EvaluationRegressionError
from zenml.evaluators.result import CaseResult
from zenml.evaluators.steps import (
    _apply_gate,
    _compute_aggregates,
    _compute_regressed_metrics,
    _mark_passed,
)


def test_compute_aggregates_basic():
    cases = [
        CaseResult(case_id="c1", scores={"f": 0.9, "r": 0.8}, passed=True),
        CaseResult(case_id="c2", scores={"f": 0.7, "r": 0.5}, passed=False),
    ]
    agg = _compute_aggregates(cases)
    assert agg["f_mean"] == pytest.approx(0.8)
    assert agg["r_mean"] == pytest.approx(0.65)
    assert agg["pass_rate"] == 0.5


def test_compute_aggregates_empty_cases():
    assert _compute_aggregates([]) == {"pass_rate": 0.0}


def test_mark_passed_no_thresholds():
    cases = [
        CaseResult(case_id="c1", scores={"f": 0.5}, passed=False),
    ]
    out = _mark_passed(cases, pass_thresholds=None)
    # No thresholds -> all pass.
    assert all(c.passed for c in out)


def test_mark_passed_with_thresholds():
    cases = [
        CaseResult(case_id="c1", scores={"f": 0.9, "r": 0.5}, passed=False),
        CaseResult(case_id="c2", scores={"f": 0.5, "r": 0.5}, passed=False),
    ]
    out = _mark_passed(cases, pass_thresholds={"f": 0.8})
    assert out[0].passed is True
    assert out[1].passed is False


def test_compute_regressed_metrics_no_baseline():
    assert (
        _compute_regressed_metrics(
            current={"f_mean": 0.8}, baseline=None, tolerance=0.0
        )
        == {}
    )


def test_compute_regressed_metrics_within_tolerance():
    out = _compute_regressed_metrics(
        current={"f_mean": 0.78},
        baseline={"f_mean": 0.80},
        tolerance=0.05,
    )
    assert out == {}  # 0.02 drop within 0.05 tolerance


def test_compute_regressed_metrics_beyond_tolerance():
    out = _compute_regressed_metrics(
        current={"f_mean": 0.70},
        baseline={"f_mean": 0.80},
        tolerance=0.05,
    )
    assert out == {"f_mean": pytest.approx(-0.10)}


def test_apply_gate_fail_raises():
    with pytest.raises(EvaluationRegressionError):
        _apply_gate(
            on_regression="fail",
            suite_name="s",
            regressed_metrics={"f_mean": -0.15},
            event_payload={},
        )


def test_apply_gate_warn_does_not_raise():
    _apply_gate(
        on_regression="warn",
        suite_name="s",
        regressed_metrics={"f_mean": -0.15},
        event_payload={},
    )  # no raise, no exception


def test_apply_gate_trigger_emits_event():
    with patch("zenml.evaluators.steps._emit_event") as emit:
        _apply_gate(
            on_regression="trigger",
            suite_name="s",
            regressed_metrics={"f_mean": -0.15},
            event_payload={"some": "payload"},
        )
    emit.assert_called_once()


def test_apply_gate_no_regression_no_op():
    with patch("zenml.evaluators.steps._emit_event") as emit:
        _apply_gate(
            on_regression="trigger",
            suite_name="s",
            regressed_metrics={},
            event_payload={},
        )
    emit.assert_not_called()
