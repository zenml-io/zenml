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
"""End-to-end smoke tests for the evaluator orchestration layer.

Shape B (orchestration-level): calls `_execute` directly, bypassing the
@step decorator.  This exercises every piece of the pipeline-facing API —
active-stack evaluator resolution, mode dispatch, pass/fail aggregation,
baseline comparison, regression detection, and gate semantics — without
requiring a real ZenML store or external network access.
"""

from typing import List, Optional, Set
from unittest.mock import patch

import pytest

from zenml.evaluators.baseline import BaselineSpec
from zenml.evaluators.cases import RAGCase
from zenml.evaluators.exceptions import (
    EvaluationModeNotSupportedError,
    EvaluationRegressionError,
)
from zenml.evaluators.result import (
    CaseResult,
    EvaluationMode,
    EvaluationResult,
)
from zenml.evaluators.steps import _execute

# ---------------------------------------------------------------------------
# In-test stub evaluator — NOT production code.
# Bypasses StackComponent.__init__ so it can be dropped directly onto a mock
# stack without going through the ZenML registry.
# ---------------------------------------------------------------------------


class _StubEvaluator:
    """Deterministic stub that only supports RAG evaluation."""

    def __init__(
        self,
        *,
        score: float = 0.9,
        supported: Optional[Set[EvaluationMode]] = None,
    ) -> None:
        self._score = score
        self._supported = (
            supported if supported is not None else {EvaluationMode.RAG}
        )
        self._flavor = "stub"

    @property
    def flavor(self) -> str:
        return self._flavor

    @property
    def supported_modes(self) -> Set[EvaluationMode]:
        return self._supported

    def evaluate_rag(
        self, cases: List[RAGCase], metrics: List[str]
    ) -> EvaluationResult:
        return EvaluationResult(
            evaluator="stub",
            mode=EvaluationMode.RAG,
            suite_name="",
            cases=[
                CaseResult(
                    case_id=str(i),
                    scores={m: self._score for m in metrics},
                    passed=True,
                )
                for i, _ in enumerate(cases)
            ],
            aggregates={},
            metadata={},
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RAG_CASES = [
    RAGCase(query="q1", context=["ctx1"], response="r1"),
    RAGCase(query="q2", context=["ctx2"], response="r2"),
]
_METRICS = ["faithfulness", "relevance"]


def _run_execute(
    *,
    evaluator: _StubEvaluator,
    baseline_result: Optional[EvaluationResult] = None,
    on_regression: str = "warn",
    pass_thresholds: Optional[dict] = None,
    regression_tolerance: float = 0.0,
) -> EvaluationResult:
    """Drive `_execute` with mocked Client and resolve_baseline."""
    with (
        patch("zenml.evaluators.steps.Client") as MockClient,
        patch(
            "zenml.evaluators.steps.resolve_baseline",
            return_value=baseline_result,
        ),
    ):
        MockClient.return_value.active_stack.evaluator = evaluator
        return _execute(
            mode=EvaluationMode.RAG,
            invoke=lambda ev: ev.evaluate_rag(_RAG_CASES, _METRICS),
            suite_name="test_suite",
            baseline=BaselineSpec(strategy="none"),
            on_regression=on_regression,
            pass_thresholds=pass_thresholds,
            regression_tolerance=regression_tolerance,
        )


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


def test_happy_path_no_baseline() -> None:
    """EvaluationResult has correct aggregates when no baseline exists."""
    stub = _StubEvaluator(score=0.9)
    result = _run_execute(evaluator=stub, baseline_result=None)

    assert result.aggregates["pass_rate"] == pytest.approx(1.0)
    assert result.aggregates["faithfulness_mean"] == pytest.approx(0.9)
    assert result.aggregates["relevance_mean"] == pytest.approx(0.9)
    assert result.metadata.get("regressed") is None
    assert len(result.cases) == 2
    assert all(c.passed for c in result.cases)


def test_baseline_no_regression_gate_is_noop() -> None:
    """When current scores beat the baseline, no exception is raised and
    the result is not flagged as regressed."""
    baseline = EvaluationResult(
        evaluator="stub",
        mode=EvaluationMode.RAG,
        suite_name="test_suite",
        cases=[],
        aggregates={"faithfulness_mean": 0.7, "relevance_mean": 0.7},
        metadata={},
    )
    stub = _StubEvaluator(score=0.9)
    result = _run_execute(
        evaluator=stub,
        baseline_result=baseline,
        on_regression="fail",
        regression_tolerance=0.0,
    )

    assert result.aggregates["faithfulness_mean"] == pytest.approx(0.9)
    assert result.metadata.get("regressed") is None


def test_regression_with_on_regression_fail_raises() -> None:
    """_execute raises EvaluationRegressionError when on_regression='fail'
    and current scores drop below the baseline beyond tolerance."""
    baseline = EvaluationResult(
        evaluator="stub",
        mode=EvaluationMode.RAG,
        suite_name="test_suite",
        cases=[],
        aggregates={"faithfulness_mean": 0.95, "relevance_mean": 0.95},
        metadata={},
    )
    stub = _StubEvaluator(score=0.7)
    with pytest.raises(EvaluationRegressionError) as exc_info:
        _run_execute(
            evaluator=stub,
            baseline_result=baseline,
            on_regression="fail",
            regression_tolerance=0.0,
        )

    err = exc_info.value
    assert err.suite_name == "test_suite"
    assert "faithfulness_mean" in err.regressed_metrics
    assert err.regressed_metrics["faithfulness_mean"] < 0


def test_regression_with_on_regression_warn_sets_metadata() -> None:
    """_execute does NOT raise when on_regression='warn', but the result
    carries regressed=True and lists the affected metrics."""
    baseline = EvaluationResult(
        evaluator="stub",
        mode=EvaluationMode.RAG,
        suite_name="test_suite",
        cases=[],
        aggregates={"faithfulness_mean": 0.95, "relevance_mean": 0.95},
        metadata={},
    )
    stub = _StubEvaluator(score=0.7)
    result = _run_execute(
        evaluator=stub,
        baseline_result=baseline,
        on_regression="warn",
        regression_tolerance=0.0,
    )

    assert result.metadata.get("regressed") is True
    assert "faithfulness_mean" in result.metadata["regressed_metrics"]


def test_unsupported_mode_raises() -> None:
    """_execute raises EvaluationModeNotSupportedError when the stub only
    supports RAG but evaluate_rag is called on an evaluator that declares
    only POINTWISE support."""
    pointwise_only = _StubEvaluator(
        supported={EvaluationMode.POINTWISE},
    )
    with (
        patch("zenml.evaluators.steps.Client") as MockClient,
        patch("zenml.evaluators.steps.resolve_baseline", return_value=None),
    ):
        MockClient.return_value.active_stack.evaluator = pointwise_only
        with pytest.raises(EvaluationModeNotSupportedError) as exc_info:
            _execute(
                mode=EvaluationMode.RAG,
                invoke=lambda ev: ev.evaluate_rag(_RAG_CASES, _METRICS),
                suite_name="test_suite",
                baseline=BaselineSpec(strategy="none"),
                on_regression="warn",
                pass_thresholds=None,
                regression_tolerance=0.0,
            )

    err = exc_info.value
    assert err.flavor == "stub"
    assert err.mode == EvaluationMode.RAG


def test_no_evaluator_in_stack_raises_runtime_error() -> None:
    """_execute raises RuntimeError when the active stack has no evaluator."""
    with (
        patch("zenml.evaluators.steps.Client") as MockClient,
        patch("zenml.evaluators.steps.resolve_baseline", return_value=None),
    ):
        MockClient.return_value.active_stack.evaluator = None
        with pytest.raises(RuntimeError, match="No evaluator configured"):
            _execute(
                mode=EvaluationMode.RAG,
                invoke=lambda ev: ev.evaluate_rag(_RAG_CASES, _METRICS),
                suite_name="test_suite",
                baseline=BaselineSpec(strategy="none"),
                on_regression="warn",
                pass_thresholds=None,
                regression_tolerance=0.0,
            )


def test_pass_thresholds_applied_before_aggregation() -> None:
    """Cases that fall below a pass_threshold are marked failed, and this
    is reflected in pass_rate even when the raw stub scores are all 0.9."""
    # faithfulness threshold of 0.95 means all cases fail (score=0.9).
    stub = _StubEvaluator(score=0.9)
    result = _run_execute(
        evaluator=stub,
        baseline_result=None,
        pass_thresholds={"faithfulness": 0.95},
    )

    assert result.aggregates["pass_rate"] == pytest.approx(0.0)
    assert all(not c.passed for c in result.cases)


def test_regression_tolerance_absorbs_small_drop() -> None:
    """A drop within the configured tolerance does not trigger a regression."""
    # Baseline is 0.85, current is 0.82 — a drop of 0.03.
    # Tolerance of 0.05 should absorb this.
    baseline = EvaluationResult(
        evaluator="stub",
        mode=EvaluationMode.RAG,
        suite_name="test_suite",
        cases=[],
        aggregates={"faithfulness_mean": 0.85, "relevance_mean": 0.85},
        metadata={},
    )
    stub = _StubEvaluator(score=0.82)
    result = _run_execute(
        evaluator=stub,
        baseline_result=baseline,
        on_regression="fail",
        regression_tolerance=0.05,
    )

    # No exception raised, and result not flagged as regressed.
    assert result.metadata.get("regressed") is None
