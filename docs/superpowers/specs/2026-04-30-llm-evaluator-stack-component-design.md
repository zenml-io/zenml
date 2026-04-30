# Design: First-class LLM Evaluation as a ZenML Stack Component

**Status:** Draft RFC
**Date:** 2026-04-30
**Author:** Demian Havdun
**Phase:** 1 of 3 (LLM eval first; classical ML eval mirror follows in Phase 2)

## Summary

Introduce **`evaluator`** as a new ZenML stack component type — peer to `experiment_tracker` and `model_registry` — that makes LLM evaluation a first-class concept. Pipelines call typed `evaluate_*` steps that resolve the active stack's evaluator, produce an `EvaluationResult` artifact, compare against a baseline (typically pulled from the model registry), and gate the run via the existing event-trigger system.

The chunk is sized to land as one feature branch: a new component type, a base interface, three eval modes, two ship-with flavors, a typed result artifact, dashboard rendering, and a new event type.

## Goals

- Make LLM evaluation a first-class, pluggable concept in ZenML — not a per-user bolt-on.
- Enable "compare-to-baseline" gating without coupling pipelines to specific eval libraries.
- Reuse existing ZenML primitives (stack components, model registry, event triggers, typed artifacts) rather than introducing parallel machinery.
- Establish an abstraction that the classical-ML mirror (Phase 2) can drop into without re-litigating shape.

## Non-goals (v1)

Listed up front so reviewers don't have to ask:

- Pairwise eval (A vs. B preference scoring).
- Agent-trajectory eval (steps, tool use, success-of-trajectory).
- LLM-judge cost tracking.
- Auto-generation of eval datasets.
- Cross-pipeline result aggregation / leaderboards.
- Eval-dataset versioning as a new artifact kind (existing artifact mechanisms suffice).
- Classical ML eval (Phase 2).

## Locked-in decisions

These were settled during brainstorming and shape everything below:

| Decision | Choice |
|---|---|
| Phase order | LLM eval first, classical mirror in Phase 2 |
| Where it lives | New stack component type (`evaluator`) |
| Eval modes in v1 | Pointwise, reference-based, RAG |
| Ship-with flavors | `OpenAIEvaluator`, `RagasEvaluator` |
| Baseline source | Model registry (primary) + explicit override |
| Gate behavior | User-configurable; default `trigger-only` |

## Architecture

### Module layout

```
src/zenml/evaluators/
    __init__.py                  # public API: evaluate_pointwise, evaluate_reference, evaluate_rag, case types, enums
    base_evaluator.py            # BaseEvaluator, BaseEvaluatorConfig, BaseEvaluatorFlavor
    cases.py                     # PointwiseCase, ReferenceCase, RAGCase, Rubric
    result.py                    # EvaluationResult, CaseResult, EvaluationMode enum
    steps.py                     # built-in @step functions: evaluate_pointwise/reference/rag
    baseline.py                  # baseline resolution logic
    events.py                    # EvalRegression event type
    materializer.py              # EvaluationResultMaterializer

src/zenml/integrations/openai/evaluators/
    openai_evaluator.py
    openai_evaluator_flavor.py

src/zenml/integrations/ragas/                # new integration package
    __init__.py
    evaluators/
        ragas_evaluator.py
        ragas_evaluator_flavor.py
```

### `BaseEvaluator` interface

```python
# src/zenml/evaluators/base_evaluator.py

class EvaluationMode(StrEnum):
    POINTWISE = "pointwise"
    REFERENCE = "reference"
    RAG = "rag"

class BaseEvaluatorConfig(StackComponentConfig):
    """Base config for evaluators. Concrete flavors extend this."""

class BaseEvaluator(StackComponent, ABC):
    """Base class for all evaluator stack components."""

    @property
    @abstractmethod
    def supported_modes(self) -> set[EvaluationMode]:
        """Modes this flavor implements. Used for compile-time validation."""

    def evaluate_pointwise(
        self,
        cases: list[PointwiseCase],
        rubric: Rubric,
    ) -> EvaluationResult:
        raise EvaluationModeNotSupportedError(self.flavor, EvaluationMode.POINTWISE)

    def evaluate_reference(
        self,
        cases: list[ReferenceCase],
        metrics: list[ReferenceMetric],
    ) -> EvaluationResult:
        raise EvaluationModeNotSupportedError(self.flavor, EvaluationMode.REFERENCE)

    def evaluate_rag(
        self,
        cases: list[RAGCase],
        metrics: list[RAGMetric],
    ) -> EvaluationResult:
        raise EvaluationModeNotSupportedError(self.flavor, EvaluationMode.RAG)
```

Default implementations raise so flavors can opt in to modes incrementally without boilerplate. `supported_modes` drives compile-time validation: calling `evaluate_rag` in a pipeline when the active stack's evaluator doesn't list `RAG` fails at pipeline build, not at runtime.

### Case types

Typed Pydantic models — one per mode — make inputs explicit and validated.

```python
# src/zenml/evaluators/cases.py

class PointwiseCase(BaseModel):
    input: str
    output: str
    metadata: dict[str, Any] = Field(default_factory=dict)

class ReferenceCase(BaseModel):
    input: str
    output: str
    expected: str
    metadata: dict[str, Any] = Field(default_factory=dict)

class RAGCase(BaseModel):
    query: str
    context: list[str]
    response: str
    expected_answer: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

class Rubric(BaseModel):
    """A scoring rubric for pointwise eval."""
    name: str
    criterion: str          # e.g. "Is the answer factually correct?"
    scale: tuple[int, int]  # e.g. (1, 5)
    examples: list[RubricExample] = Field(default_factory=list)
```

### `EvaluationResult` artifact

```python
# src/zenml/evaluators/result.py

class CaseResult(BaseModel):
    case_id: str
    scores: dict[str, float]   # metric name -> score
    passed: bool                # against thresholds
    raw: dict[str, Any] = Field(default_factory=dict)  # judge output, traces

class EvaluationResult(BaseModel):
    evaluator: str              # flavor name (e.g. "openai")
    mode: EvaluationMode
    suite_name: str             # logical name; baseline join key
    cases: list[CaseResult]
    aggregates: dict[str, float]  # mean, p50, p95, pass_rate per metric
    metadata: dict[str, Any]    # model_version_id, dataset_ref, evaluator_config_hash
```

Registered as a typed artifact with a custom materializer. Dashboard renders it via a new `EvaluationResultViz` component (same hook used today for `HTMLString` artifacts).

### Invocation API

Pre-built `@step` functions in `zenml.evaluators.steps`. Users import and call them directly inside pipelines — no `Client().active_stack` access in user code:

```python
from zenml import pipeline
from zenml.evaluators import evaluate_rag, RAGCase

@pipeline
def rag_pipeline(query: str):
    response, context = my_rag_step(query)
    evaluate_rag(
        cases=[RAGCase(query=query, context=context, response=response)],
        metrics=["faithfulness", "answer_relevance"],
        suite_name="rag_quality",
        baseline="model_registry",            # default
        on_regression="trigger",              # default; "fail" | "warn" | "trigger"
        pass_thresholds={"faithfulness": 0.8},      # per-case pass/fail
        regression_tolerance=0.0,                    # aggregate vs. baseline
    )
```

Two distinct knobs, kept separate by design:

- **`pass_thresholds`** — per-case pass/fail criteria. A case "passes" if every listed metric is at or above its threshold. Drives `CaseResult.passed` and the `pass_rate` aggregate. Optional; absent means all cases pass.
- **`regression_tolerance`** — how much an aggregate metric is allowed to drop versus the baseline aggregate before it counts as a regression. Default `0.0` (any drop regresses); set higher to absorb judge variance. Has no effect when there is no baseline.

The `evaluate_rag` step body:
1. Resolves `Client().active_stack.evaluator` (compile-time check that one is configured and supports `RAG`).
2. Calls `evaluator.evaluate_rag(cases, metrics)`.
3. Computes per-case `passed` from `pass_thresholds` and aggregates (mean, p50, p95, pass_rate).
4. Resolves baseline via `baseline.py` helpers.
5. Computes regression: any aggregate metric below baseline by more than `regression_tolerance` → regressed.
6. Applies gate (`fail` raises, `warn` flags artifact, `trigger` emits `EvalRegression` event).
7. Returns the `EvaluationResult` artifact (auto-linked to the run's active model version, if any, via the existing model-registry linkage).

### Baseline resolution

`src/zenml/evaluators/baseline.py` resolves in this order:

1. **Explicit** — `baseline_run_id` or `baseline_artifact_id` passed to the step.
2. **Model registry** — fetch the most recent `EvaluationResult` linked to the model version currently marked `production` in the registry, filtered by `suite_name` and `mode`. Uses the existing model–artifact linkage; no new schema.
3. **None** — first run with no eligible baseline. Result is recorded with `baseline=None`; no gate fires.

The `suite_name` is the join key — it lets users have multiple eval suites per pipeline (e.g., `"safety"`, `"rag_quality"`) compared independently.

### Gate semantics

- **`on_regression="trigger"` (default)** — emits an `EvalRegression` event with the result artifact ID, suite name, regression delta, and run context. The existing event-trigger system routes it to user-configured handlers (Slack, PagerDuty, follow-up pipelines). Run continues normally.
- **`on_regression="fail"`** — raises `EvaluationRegressionError`; run is marked failed; downstream steps skip via the existing failure-skip semantics.
- **`on_regression="warn"`** — attaches `regressed=True` plus the delta to the artifact metadata; run continues; no event.

Default is `trigger` deliberately: eval-as-signal rather than eval-as-control-flow. LLM judges have variance; defaulting to hard-fail traps users into runs failing because the judge had a bad day. Hard-fail is opt-in for users who want strict gating.

### Event integration

`EvalRegression` registered as a new event source via `src/zenml/evaluators/events.py`, piggybacking on the recent event-trigger work (commits `2c84f7108`, `2b5813584`, `d81c9d724`). Payload schema:

```python
class EvalRegressionEvent(BaseEvent):
    suite_name: str
    mode: EvaluationMode
    evaluator: str
    pipeline_run_id: UUID
    artifact_id: UUID
    aggregates: dict[str, float]
    baseline_aggregates: dict[str, float]
    regressed_metrics: dict[str, float]   # metric -> delta
    model_version_id: UUID | None
```

Users wire this through the existing trigger CLI/UI. No new trigger machinery — only a new event source.

### Stack component integration

- **`StackComponentType` enum** (`src/zenml/enums.py`): add `EVALUATOR = "evaluator"`.
- **CLI**: `zenml evaluator register/list/delete/describe/update` auto-generated from the existing stack-component CLI machinery (no per-component CLI code needed beyond flavor registration).
- **Stack validation**: evaluator is **optional** in a stack. Pipelines calling `evaluate_*` steps without a configured evaluator fail at pipeline-build time with: `"No evaluator configured in active stack 'X'. Register one with: zenml evaluator register ..."`. Compile-time, not runtime.
- **Migration**: a single Alembic revision adding the `evaluator` enum value to `stack_component.type`. No schema change beyond the enum.

### Dashboard

The dashboard work is the only piece that crosses repo boundaries (lives in the dashboard repo, not core). Two additions:

1. **`EvaluationResultViz`** — a renderer for the `EvaluationResult` artifact. Shows: per-case scores in a sortable table, aggregate metrics with baseline diffs, pass/fail badges, raw judge output expandable per case.
2. **Evaluations tab on the model-version page** — shows trend of evaluation aggregates across the last N model versions, grouped by `suite_name`. Pulls existing artifact–model-version links; no new API.

The pipeline-run detail page links to the evaluation artifact via the existing artifact-output rendering — no new page needed there in v1.

## Concrete flavors

### `OpenAIEvaluator`

- **Modes:** `{POINTWISE, REFERENCE, RAG}`
- **Config:** `model` (default `gpt-4o-mini`), `api_key` (via secret), `temperature`, `max_concurrency`.
- **Pointwise:** structured-output rubric scoring; uses `response_format` for stable JSON.
- **Reference:** semantic-equivalence judging; falls back to exact/fuzzy match if `metric="exact"`.
- **RAG:** in-prompt rubric for `faithfulness`, `answer_relevance`, `context_relevance` — same shape as Ragas's metrics so users can A/B the judges.

### `RagasEvaluator`

- **Modes:** `{REFERENCE, RAG}` (Ragas doesn't natively do free-form pointwise scoring).
- **Config:** `judge_model_provider` (openai/anthropic/local), `embedding_model`, supported metric subset.
- **Reference:** Ragas's answer-correctness, answer-similarity.
- **RAG:** Ragas's faithfulness, answer relevancy, context precision/recall.

Two flavors prove the abstraction isn't shaped to one library. They expose overlapping capabilities under the same case types and metric names where possible, so users can swap the judge backend without changing pipeline code.

## Code-touch summary

New code:
- `src/zenml/evaluators/` — new module (~7 files, mostly small).
- `src/zenml/integrations/openai/evaluators/` — flavor + implementation.
- `src/zenml/integrations/ragas/` — new integration package.
- New Alembic migration — single revision, enum-only.
- Tests: `tests/unit/evaluators/` — base class, baseline resolution, gate semantics, case validation, result aggregation.
- Integration tests: per-flavor smoke tests gated on API keys (mirrors how `openai` integration is tested today).
- Docs: `docs/book/component-guide/evaluators/` (overview + per-flavor pages) + LLMOps how-to guide.

Modifications:
- `src/zenml/enums.py` — add `EVALUATOR` to `StackComponentType`.
- `src/zenml/stack/stack.py` — wire evaluator into `Stack` (optional component, like `experiment_tracker`).
- `src/zenml/stack/stack_validator.py` — pipeline-build-time validation that referenced eval modes are supported.
- Trigger event-source registry — register `EvalRegression`.
- `src/zenml/integrations/openai/__init__.py` — register the flavor.
- Dashboard repo (separate PR) — `EvaluationResultViz`, model-version evaluations tab.

## Phasing

- **Phase 1 (this RFC)** — everything above. Single feature branch, likely a stack of PRs: (a) base abstraction + result artifact + baseline + gate; (b) `OpenAIEvaluator` flavor; (c) `RagasEvaluator` flavor + new integration package; (d) dashboard render.
- **Phase 2 (follow-up RFC)** — `ModelEvaluator` for classical ML. Reuses `EvaluationResult`, adds `ClassificationCase` / `RegressionCase`, mirrors gate semantics. Most of the framework code is shared; only new code is case types and concrete flavors (e.g., a `SklearnEvaluator`).
- **Phase 3** — pairwise eval, agent-trajectory eval, more flavors (DeepEval, Phoenix Arize), eval-dataset registry as a typed artifact kind.

## Open questions for reviewers

These are deliberately left for the RFC discussion, not pre-decided in this spec:

1. Should `Ragas` be a separate flavor, or consolidated into `OpenAIEvaluator` (since Ragas can use OpenAI as its judge)? Current design: separate, to prove the abstraction; a reviewer may argue it's redundant.
2. Should `EvalRegression` be a single event type with a `severity` field, or split into `EvalRegression` / `EvalCriticalRegression`? Current design: single event with full delta in payload, severity inferred by handlers.
3. Per-metric regression tolerance: v1 uses a single scalar `regression_tolerance` applied to every metric. A reviewer may push for per-metric tolerances (e.g., `{"faithfulness": 0.05, "answer_relevance": 0.10}`). Current design: scalar in v1; per-metric is Phase 2.
4. Should evaluators be allowed to mutate inputs (e.g., redact PII before sending to judge)? Current design: no — evaluators are read-only over their inputs; pre-processing is a separate user step.

## Risks

- **LLM judge variance** — eval results are stochastic. Mitigations: default to `trigger` (not `fail`); document `temperature=0` and seeding; allow `n_runs` per case with mean/median aggregation in the future (not v1).
- **Ragas API churn** — Ragas is young and changes often. Mitigation: pin a known-good version range in the integration's extras; the abstraction shields users from direct Ragas imports.
- **Dashboard repo coordination** — the renderer lives in a separate repo. Mitigation: ship core without renderer first; the artifact has a working JSON view by default.
- **Scope creep in review** — reviewers may push to add pairwise/agent eval. Mitigation: this spec lists them as Phase 3 explicitly.
