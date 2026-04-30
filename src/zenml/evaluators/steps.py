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
"""Pre-built ZenML steps that invoke the active stack's evaluator."""

import statistics
from typing import Any, Callable, Dict, List, Literal, Optional

from zenml import step
from zenml.client import Client
from zenml.evaluators.baseline import BaselineSpec, resolve_baseline
from zenml.evaluators.cases import (
    PointwiseCase,
    RAGCase,
    ReferenceCase,
    Rubric,
)
from zenml.evaluators.exceptions import (
    EvaluationModeNotSupportedError,
    EvaluationRegressionError,
)
from zenml.evaluators.result import (
    CaseResult,
    EvaluationMode,
    EvaluationResult,
)
from zenml.logger import get_logger

logger = get_logger(__name__)

OnRegression = Literal["fail", "warn", "trigger"]


def _compute_aggregates(cases: List[CaseResult]) -> Dict[str, float]:
    """Mean per metric and overall pass_rate.

    Args:
        cases: Per-case results.

    Returns:
        Dict mapping `{metric}_mean` -> mean score, plus `pass_rate`.
    """
    if not cases:
        return {"pass_rate": 0.0}
    metric_names: set = set()
    for c in cases:
        metric_names.update(c.scores.keys())
    agg: Dict[str, float] = {}
    for m in metric_names:
        values = [c.scores[m] for c in cases if m in c.scores]
        if values:
            agg[f"{m}_mean"] = statistics.fmean(values)
    agg["pass_rate"] = sum(1 for c in cases if c.passed) / len(cases)
    return agg


def _mark_passed(
    cases: List[CaseResult],
    pass_thresholds: Optional[Dict[str, float]],
) -> List[CaseResult]:
    """Return cases with `passed` recomputed against the supplied thresholds.

    If no thresholds are supplied, every case is considered passed.

    Args:
        cases: Original per-case results.
        pass_thresholds: Optional mapping from metric -> minimum score.

    Returns:
        New list of CaseResult instances with `passed` updated.
    """
    if not pass_thresholds:
        return [c.model_copy(update={"passed": True}) for c in cases]

    out: List[CaseResult] = []
    for c in cases:
        ok = all(
            c.scores.get(m, float("-inf")) >= thr
            for m, thr in pass_thresholds.items()
        )
        out.append(c.model_copy(update={"passed": ok}))
    return out


def _compute_regressed_metrics(
    current: Dict[str, float],
    baseline: Optional[Dict[str, float]],
    tolerance: float,
) -> Dict[str, float]:
    """Return metric -> delta for metrics that regressed beyond tolerance.

    Delta is negative (current - baseline). Tolerance is the maximum
    absolute drop that's still considered acceptable.

    Args:
        current: Aggregates from the current run.
        baseline: Aggregates from the baseline; None means no baseline.
        tolerance: Maximum acceptable drop (>=0).

    Returns:
        Dict of regressed metrics with their (negative) deltas.
    """
    if not baseline:
        return {}
    regressed: Dict[str, float] = {}
    for metric, base_val in baseline.items():
        if metric not in current:
            continue
        delta = current[metric] - base_val
        if delta < -abs(tolerance):
            regressed[metric] = delta
    return regressed


def _apply_gate(
    on_regression: OnRegression,
    suite_name: str,
    regressed_metrics: Dict[str, float],
    event_payload: Dict[str, Any],
) -> None:
    """Apply the configured gate behavior. No-op if no regression.

    Args:
        on_regression: "fail" | "warn" | "trigger".
        suite_name: For error messages.
        regressed_metrics: Metric -> delta map; empty means no regression.
        event_payload: Payload passed to _emit_event for "trigger" mode.

    Raises:
        EvaluationRegressionError: When on_regression="fail" and there's a regression.
        ValueError: When on_regression is not a recognized value.
    """
    if not regressed_metrics:
        return
    if on_regression == "fail":
        raise EvaluationRegressionError(suite_name, regressed_metrics)
    if on_regression == "warn":
        logger.warning(
            "Evaluator regressed (suite=%s, metrics=%s); on_regression='warn'",
            suite_name,
            regressed_metrics,
        )
        return
    if on_regression == "trigger":
        _emit_event(event_payload)
        return
    raise ValueError(f"Unknown on_regression mode: {on_regression}")


def _emit_event(payload: Dict[str, Any]) -> None:
    """Emit an EvalRegression event.

    NOTE: ZenML's existing EventDispatcher (src/zenml/dispatcher/dispatcher.py)
    only routes pipeline-run-status events. There is no general-purpose
    event-emission API yet for custom payload types. For v1 we log the
    payload at INFO level; routing into the trigger system is a Phase 1.5
    follow-up — see GitHub discussion #4787.
    """
    logger.info("EvalRegression event: %s", payload)
    # TODO(future): once a general event-emission API exists, route the
    # payload through it. Construct EvalRegressionEvent(**payload) and
    # dispatch via the trigger system.


def _execute(
    mode: EvaluationMode,
    invoke: Callable[[Any], EvaluationResult],
    suite_name: str,
    baseline: Optional[BaselineSpec],
    on_regression: OnRegression,
    pass_thresholds: Optional[Dict[str, float]],
    regression_tolerance: float,
) -> EvaluationResult:
    """Shared body for the three evaluate_* steps.

    Args:
        mode: Evaluation mode to run.
        invoke: Callable that accepts an evaluator and returns a raw result.
        suite_name: Logical name for this eval suite; used to match baselines.
        baseline: How to resolve the comparison baseline; defaults to
            model_registry strategy when None.
        on_regression: Action when regression is detected.
        pass_thresholds: Per-metric minimum scores for per-case pass/fail.
        regression_tolerance: Maximum acceptable absolute drop before flagging.

    Returns:
        The final EvaluationResult with aggregates and pass/fail applied.

    Raises:
        RuntimeError: If no evaluator is configured in the active stack.
        EvaluationModeNotSupportedError: If the active evaluator doesn't support mode.
        EvaluationRegressionError: If on_regression="fail" and regression detected.
    """
    if baseline is None:
        baseline = BaselineSpec(strategy="model_registry")

    client = Client()
    evaluator = client.active_stack.evaluator
    if evaluator is None:
        raise RuntimeError(
            "No evaluator configured in the active stack. "
            "Register one with `zenml evaluator register ...`."
        )
    if mode not in evaluator.supported_modes:
        raise EvaluationModeNotSupportedError(evaluator.flavor, mode)

    raw_result = invoke(evaluator)
    cases = _mark_passed(raw_result.cases, pass_thresholds)
    aggregates = _compute_aggregates(cases)
    raw_result = raw_result.model_copy(
        update={
            "cases": cases,
            "aggregates": aggregates,
            "suite_name": suite_name,
        }
    )

    base_result = resolve_baseline(baseline, suite_name, mode)
    regressed = _compute_regressed_metrics(
        aggregates,
        base_result.aggregates if base_result else None,
        regression_tolerance,
    )
    if regressed:
        raw_result = raw_result.model_copy(
            update={
                "metadata": {
                    **raw_result.metadata,
                    "regressed": True,
                    "regressed_metrics": regressed,
                }
            }
        )

    payload = {
        "suite_name": suite_name,
        "mode": str(mode),
        "evaluator": evaluator.flavor,
        "aggregates": aggregates,
        "baseline_aggregates": (base_result.aggregates if base_result else {}),
        "regressed_metrics": regressed,
    }
    _apply_gate(on_regression, suite_name, regressed, payload)
    return raw_result


@step
def evaluate_pointwise(
    cases: List[PointwiseCase],
    rubric: Rubric,
    suite_name: str,
    baseline: Optional[BaselineSpec] = None,
    on_regression: OnRegression = "trigger",
    pass_thresholds: Optional[Dict[str, float]] = None,
    regression_tolerance: float = 0.0,
) -> EvaluationResult:
    """Run pointwise eval and gate the run on regression.

    Args:
        cases: The pointwise cases to evaluate.
        rubric: Scoring rubric to apply to each case.
        suite_name: Logical name for this eval suite.
        baseline: How to resolve the comparison baseline. Defaults to
            model_registry strategy when None.
        on_regression: Action when regression detected: "fail", "warn", or
            "trigger".
        pass_thresholds: Per-metric minimum scores for per-case pass/fail.
        regression_tolerance: Maximum acceptable absolute drop before flagging.

    Returns:
        EvaluationResult with per-case scores, aggregates, and pass/fail.
    """
    return _execute(
        mode=EvaluationMode.POINTWISE,
        invoke=lambda ev: ev.evaluate_pointwise(cases, rubric),
        suite_name=suite_name,
        baseline=baseline,
        on_regression=on_regression,
        pass_thresholds=pass_thresholds,
        regression_tolerance=regression_tolerance,
    )


@step
def evaluate_reference(
    cases: List[ReferenceCase],
    metrics: List[str],
    suite_name: str,
    baseline: Optional[BaselineSpec] = None,
    on_regression: OnRegression = "trigger",
    pass_thresholds: Optional[Dict[str, float]] = None,
    regression_tolerance: float = 0.0,
) -> EvaluationResult:
    """Run reference-based eval and gate the run on regression.

    Args:
        cases: The reference cases to evaluate.
        metrics: Metric names to compute.
        suite_name: Logical name for this eval suite.
        baseline: How to resolve the comparison baseline. Defaults to
            model_registry strategy when None.
        on_regression: Action when regression detected: "fail", "warn", or
            "trigger".
        pass_thresholds: Per-metric minimum scores for per-case pass/fail.
        regression_tolerance: Maximum acceptable absolute drop before flagging.

    Returns:
        EvaluationResult with per-case scores, aggregates, and pass/fail.
    """
    return _execute(
        mode=EvaluationMode.REFERENCE,
        invoke=lambda ev: ev.evaluate_reference(cases, metrics),
        suite_name=suite_name,
        baseline=baseline,
        on_regression=on_regression,
        pass_thresholds=pass_thresholds,
        regression_tolerance=regression_tolerance,
    )


@step
def evaluate_rag(
    cases: List[RAGCase],
    metrics: List[str],
    suite_name: str,
    baseline: Optional[BaselineSpec] = None,
    on_regression: OnRegression = "trigger",
    pass_thresholds: Optional[Dict[str, float]] = None,
    regression_tolerance: float = 0.0,
) -> EvaluationResult:
    """Run RAG eval and gate the run on regression.

    Args:
        cases: The RAG cases to evaluate (query, context, response triples).
        metrics: Metric names to compute.
        suite_name: Logical name for this eval suite.
        baseline: How to resolve the comparison baseline. Defaults to
            model_registry strategy when None.
        on_regression: Action when regression detected: "fail", "warn", or
            "trigger".
        pass_thresholds: Per-metric minimum scores for per-case pass/fail.
        regression_tolerance: Maximum acceptable absolute drop before flagging.

    Returns:
        EvaluationResult with per-case scores, aggregates, and pass/fail.
    """
    return _execute(
        mode=EvaluationMode.RAG,
        invoke=lambda ev: ev.evaluate_rag(cases, metrics),
        suite_name=suite_name,
        baseline=baseline,
        on_regression=on_regression,
        pass_thresholds=pass_thresholds,
        regression_tolerance=regression_tolerance,
    )
