# LLM Evaluator Stack Component Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new `evaluator` stack component type to ZenML that makes LLM evaluation a first-class concept, with a base abstraction, three eval modes (pointwise / reference / RAG), an `EvaluationResult` artifact, baseline-vs-current gating, two ship-with flavors (`OpenAIEvaluator`, `RagasEvaluator`), and event-trigger integration.

**Architecture:** A new module `src/zenml/evaluators/` defines the core abstraction (base class, typed cases, result artifact, baseline resolution, gate semantics, pre-built `@step` functions). The new `EVALUATOR` `StackComponentType` enum value plugs the component into ZenML's existing stack/CLI machinery. Two concrete flavors live in `integrations/openai/` and a new `integrations/ragas/` package, proving the abstraction is library-agnostic. The pipeline-facing API is `zenml.evaluators.evaluate_pointwise / evaluate_reference / evaluate_rag` — pre-built steps that resolve the active stack's evaluator, compare to a baseline (default: pulled from model registry), and either fail / warn / emit an `EvalRegression` event on regression.

**Tech Stack:** Python 3.10+, Pydantic v2, SQLModel/SQLAlchemy 2.0, Alembic, FastAPI (server side), pytest. Integrates with: existing `StackComponent` framework, model registry, event-trigger system (`src/zenml/event_*` and trigger registry; verify exact module location during Task 8), typed artifact materializers.

**Spec:** [`docs/superpowers/specs/2026-04-30-llm-evaluator-stack-component-design.md`](../specs/2026-04-30-llm-evaluator-stack-component-design.md)

**Conventions:**
- Run `bash scripts/format.sh` before every commit.
- Run targeted tests only (`pytest tests/unit/evaluators/...`), not the full suite.
- All commits include co-author trailer per repo convention; never `--no-verify` or `--amend`.
- US English spellings everywhere.

---

## File Structure (locked-in before tasks start)

**New files:**

```
src/zenml/evaluators/
    __init__.py                  # Public API re-exports
    base_evaluator.py            # BaseEvaluator, BaseEvaluatorConfig, BaseEvaluatorFlavor
    cases.py                     # PointwiseCase, ReferenceCase, RAGCase, Rubric, RubricExample
    result.py                    # EvaluationResult, CaseResult, EvaluationMode
    materializer.py              # EvaluationResultMaterializer
    baseline.py                  # resolve_baseline()
    events.py                    # EvalRegressionEvent
    steps.py                     # evaluate_pointwise / evaluate_reference / evaluate_rag
    exceptions.py                # EvaluationModeNotSupportedError, EvaluationRegressionError

src/zenml/integrations/openai/evaluators/
    __init__.py
    openai_evaluator.py
    openai_evaluator_flavor.py

src/zenml/integrations/ragas/                # NEW integration package
    __init__.py
    evaluators/
        __init__.py
        ragas_evaluator.py
        ragas_evaluator_flavor.py

src/zenml/zen_stores/migrations/versions/
    <hash>_add_evaluator_component_type.py    # Alembic migration (only if enum is a DB enum, see Task 9)

tests/unit/evaluators/
    __init__.py
    test_cases.py
    test_result.py
    test_baseline.py
    test_steps.py
    test_base_evaluator.py
tests/unit/integrations/openai/
    test_openai_evaluator.py
tests/unit/integrations/ragas/
    test_ragas_evaluator.py

docs/book/component-guide/evaluators/
    evaluators.md                # Section overview
    openai.md
    ragas.md
    custom.md                    # How to write your own
```

**Modified files:**

- `src/zenml/enums.py` — add `EVALUATOR = "evaluator"` to `StackComponentType`.
- `src/zenml/integrations/openai/__init__.py` — register the OpenAI evaluator flavor.
- `src/zenml/integrations/registry.py` (or wherever new integration packages register) — register `ragas` integration. Verify exact location during Task 11.
- `docs/book/component-guide/toc.md` — link the new section.

**Deliberately not modified in this plan (out of scope):**

- The dashboard repo (separate PR; tracked outside this plan).
- `ModelEvaluator` for classical ML (Phase 2; separate spec).

---

## Task 1: Add `EVALUATOR` to `StackComponentType` enum

**Files:**
- Modify: `src/zenml/enums.py:198-241`
- Test: `tests/unit/test_enums.py` (add if doesn't exist; verify path during step 1)

- [ ] **Step 1: Confirm test file path**

Run: `find /home/demian/Projects/zenml/tests/unit -name "test_enums.py" -o -name "*_enums*.py" | head -3`

If a test file exists, use it. Otherwise create `tests/unit/test_enums.py`.

- [ ] **Step 2: Write the failing test**

Add to `tests/unit/test_enums.py`:

```python
from zenml.enums import StackComponentType


def test_evaluator_in_stack_component_type():
    assert StackComponentType.EVALUATOR == "evaluator"


def test_evaluator_plural():
    assert StackComponentType.EVALUATOR.plural == "evaluators"


def test_evaluator_does_not_support_multiple_per_stack():
    # Default; flip later if user feedback wants it
    assert StackComponentType.EVALUATOR.supports_multiple_per_stack is False
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/unit/test_enums.py::test_evaluator_in_stack_component_type -v`

Expected: FAIL with `AttributeError: EVALUATOR` or similar.

- [ ] **Step 4: Add the enum value**

In `src/zenml/enums.py`, modify the `StackComponentType` class:

```python
class StackComponentType(StrEnum):
    """All possible types a `StackComponent` can have."""

    ALERTER = "alerter"
    ANNOTATOR = "annotator"
    ARTIFACT_STORE = "artifact_store"
    CONTAINER_REGISTRY = "container_registry"
    DATA_VALIDATOR = "data_validator"
    EVALUATOR = "evaluator"            # NEW
    EXPERIMENT_TRACKER = "experiment_tracker"
    FEATURE_STORE = "feature_store"
    IMAGE_BUILDER = "image_builder"
    LOG_STORE = "log_store"
    MODEL_DEPLOYER = "model_deployer"
    ORCHESTRATOR = "orchestrator"
    STEP_OPERATOR = "step_operator"
    MODEL_REGISTRY = "model_registry"
    DEPLOYER = "deployer"
```

The default `plural` returns `f"{self.value}s"` → `"evaluators"`, so no change needed in the `plural` property. The default `supports_multiple_per_stack` returns `False`, so no change needed there either.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_enums.py -v -k evaluator`

Expected: 3 passed.

- [ ] **Step 6: Run a wider sanity check**

Run: `pytest tests/unit/test_enums.py -v`

Expected: all green; no regression in pre-existing enum tests.

- [ ] **Step 7: Format and commit**

```bash
bash scripts/format.sh
git add src/zenml/enums.py tests/unit/test_enums.py
git commit -m "$(cat <<'EOF'
Add EVALUATOR to StackComponentType enum

Foundational enum value for the new evaluator stack component type.
No behavior change yet — subsequent commits register the base class,
flavors, and pipeline integration.

Part of LLM evaluator framework (Phase 1).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Define type primitives (modes, cases, rubric)

**Files:**
- Create: `src/zenml/evaluators/__init__.py`
- Create: `src/zenml/evaluators/cases.py`
- Create: `tests/unit/evaluators/__init__.py`
- Create: `tests/unit/evaluators/test_cases.py`

- [ ] **Step 1: Create empty package files**

```bash
mkdir -p /home/demian/Projects/zenml/src/zenml/evaluators
mkdir -p /home/demian/Projects/zenml/tests/unit/evaluators
```

Create `src/zenml/evaluators/__init__.py` with content:

```python
"""ZenML LLM evaluation framework.

Public API for building eval suites against LLM/agent outputs and gating
pipeline runs on regression versus a baseline.
"""
```

Create `tests/unit/evaluators/__init__.py` (empty file).

- [ ] **Step 2: Write failing tests for case types**

Create `tests/unit/evaluators/test_cases.py`:

```python
import pytest
from pydantic import ValidationError

from zenml.evaluators.cases import (
    PointwiseCase,
    RAGCase,
    ReferenceCase,
    Rubric,
    RubricExample,
)


def test_pointwise_case_minimal():
    case = PointwiseCase(input="What is 2+2?", output="4")
    assert case.input == "What is 2+2?"
    assert case.output == "4"
    assert case.metadata == {}


def test_pointwise_case_with_metadata():
    case = PointwiseCase(
        input="x", output="y", metadata={"source": "test", "id": 7}
    )
    assert case.metadata["source"] == "test"


def test_reference_case_requires_expected():
    with pytest.raises(ValidationError):
        ReferenceCase(input="x", output="y")  # missing expected


def test_reference_case_full():
    case = ReferenceCase(input="x", output="y", expected="z")
    assert case.expected == "z"


def test_rag_case_minimal():
    case = RAGCase(query="q", context=["doc1", "doc2"], response="r")
    assert case.context == ["doc1", "doc2"]
    assert case.expected_answer is None


def test_rag_case_with_expected_answer():
    case = RAGCase(
        query="q", context=["doc1"], response="r", expected_answer="ea"
    )
    assert case.expected_answer == "ea"


def test_rag_case_empty_context_allowed():
    # Edge: a question that wasn't grounded in any context.
    case = RAGCase(query="q", context=[], response="r")
    assert case.context == []


def test_rubric_with_examples():
    rubric = Rubric(
        name="factuality",
        criterion="Is the answer factually correct?",
        scale=(1, 5),
        examples=[
            RubricExample(input="i", output="o", score=4, rationale="ok"),
        ],
    )
    assert rubric.scale == (1, 5)
    assert rubric.examples[0].score == 4


def test_rubric_scale_validates_min_lt_max():
    with pytest.raises(ValidationError):
        Rubric(name="x", criterion="y", scale=(5, 1))
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/unit/evaluators/test_cases.py -v`

Expected: FAIL with `ModuleNotFoundError: zenml.evaluators.cases`.

- [ ] **Step 4: Implement `cases.py`**

Create `src/zenml/evaluators/cases.py`:

```python
"""Typed input case classes for the three evaluation modes."""

from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


class PointwiseCase(BaseModel):
    """A single (input, output) pair scored against a rubric."""

    input: str
    output: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReferenceCase(BaseModel):
    """A case with a known expected output, scored by similarity."""

    input: str
    output: str
    expected: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RAGCase(BaseModel):
    """A retrieval-augmented case: query, retrieved context, response."""

    query: str
    context: list[str]
    response: str
    expected_answer: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RubricExample(BaseModel):
    """A worked example used to anchor a rubric for an LLM judge."""

    input: str
    output: str
    score: int
    rationale: str


class Rubric(BaseModel):
    """A scoring rubric used by pointwise evaluators (e.g., LLM-as-judge)."""

    name: str
    criterion: str
    scale: tuple[int, int]
    examples: list[RubricExample] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_scale(self) -> "Rubric":
        lo, hi = self.scale
        if lo >= hi:
            raise ValueError(
                f"Rubric scale must have min < max; got ({lo}, {hi})"
            )
        return self
```

- [ ] **Step 5: Re-export from package**

Update `src/zenml/evaluators/__init__.py`:

```python
"""ZenML LLM evaluation framework.

Public API for building eval suites against LLM/agent outputs and gating
pipeline runs on regression versus a baseline.
"""

from zenml.evaluators.cases import (
    PointwiseCase,
    RAGCase,
    ReferenceCase,
    Rubric,
    RubricExample,
)

__all__ = [
    "PointwiseCase",
    "RAGCase",
    "ReferenceCase",
    "Rubric",
    "RubricExample",
]
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/unit/evaluators/test_cases.py -v`

Expected: 9 passed.

- [ ] **Step 7: Format and commit**

```bash
bash scripts/format.sh
git add src/zenml/evaluators/__init__.py src/zenml/evaluators/cases.py tests/unit/evaluators/
git commit -m "$(cat <<'EOF'
Add evaluator case types and rubric

Typed Pydantic models for the three v1 eval modes: pointwise,
reference-based, and RAG. Rubric/RubricExample anchor LLM-as-judge
prompts.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Define `EvaluationResult` artifact + `EvaluationMode`

**Files:**
- Create: `src/zenml/evaluators/result.py`
- Create: `tests/unit/evaluators/test_result.py`
- Modify: `src/zenml/evaluators/__init__.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/evaluators/test_result.py`:

```python
import pytest

from zenml.evaluators.result import (
    CaseResult,
    EvaluationMode,
    EvaluationResult,
)


def test_evaluation_mode_values():
    assert EvaluationMode.POINTWISE == "pointwise"
    assert EvaluationMode.REFERENCE == "reference"
    assert EvaluationMode.RAG == "rag"


def test_case_result_minimal():
    cr = CaseResult(case_id="c1", scores={"faithfulness": 0.9}, passed=True)
    assert cr.scores["faithfulness"] == 0.9
    assert cr.passed is True
    assert cr.raw == {}


def test_evaluation_result_aggregates_required():
    er = EvaluationResult(
        evaluator="openai",
        mode=EvaluationMode.RAG,
        suite_name="rag_quality",
        cases=[
            CaseResult(case_id="c1", scores={"f": 0.9}, passed=True),
            CaseResult(case_id="c2", scores={"f": 0.7}, passed=False),
        ],
        aggregates={"f_mean": 0.8, "pass_rate": 0.5},
        metadata={},
    )
    assert er.aggregates["pass_rate"] == 0.5
    assert len(er.cases) == 2


def test_evaluation_result_empty_cases_allowed():
    # Edge: dataset filtered to nothing — still a valid result.
    er = EvaluationResult(
        evaluator="openai",
        mode=EvaluationMode.POINTWISE,
        suite_name="x",
        cases=[],
        aggregates={},
        metadata={},
    )
    assert er.cases == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/evaluators/test_result.py -v`

Expected: FAIL with `ModuleNotFoundError: zenml.evaluators.result`.

- [ ] **Step 3: Implement `result.py`**

Create `src/zenml/evaluators/result.py`:

```python
"""Output artifact types for the evaluator framework."""

from typing import Any

from pydantic import BaseModel, Field

from zenml.utils.enum_utils import StrEnum


class EvaluationMode(StrEnum):
    """The evaluation mode this result was produced under."""

    POINTWISE = "pointwise"
    REFERENCE = "reference"
    RAG = "rag"


class CaseResult(BaseModel):
    """Per-case outcome from an evaluator."""

    case_id: str
    scores: dict[str, float]
    passed: bool
    raw: dict[str, Any] = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    """Output of one evaluator run; emitted as a typed artifact."""

    evaluator: str
    mode: EvaluationMode
    suite_name: str
    cases: list[CaseResult]
    aggregates: dict[str, float]
    metadata: dict[str, Any] = Field(default_factory=dict)
```

Verify the `StrEnum` import path: ZenML has its own `StrEnum` (commit `4d3b9ac7b` mentions "Fix StrEnum import breaking 3.10"). If `zenml.utils.enum_utils.StrEnum` doesn't exist, run:

```bash
grep -rn "class StrEnum" /home/demian/Projects/zenml/src/zenml/ | head -5
```

…and import from the discovered location.

- [ ] **Step 4: Re-export from package**

Update `src/zenml/evaluators/__init__.py`, adding to existing imports:

```python
from zenml.evaluators.result import (
    CaseResult,
    EvaluationMode,
    EvaluationResult,
)
```

…and to `__all__`:

```python
"CaseResult",
"EvaluationMode",
"EvaluationResult",
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/unit/evaluators/test_result.py -v`

Expected: 4 passed.

- [ ] **Step 6: Format and commit**

```bash
bash scripts/format.sh
git add src/zenml/evaluators/result.py src/zenml/evaluators/__init__.py tests/unit/evaluators/test_result.py
git commit -m "$(cat <<'EOF'
Add EvaluationResult artifact and EvaluationMode enum

Typed result artifact emitted by all evaluator implementations.
CaseResult holds per-case scores; EvaluationResult holds aggregate
metrics plus model-version/dataset metadata for baseline comparison.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: `EvaluationResultMaterializer`

**Files:**
- Create: `src/zenml/evaluators/materializer.py`
- Create: `tests/unit/evaluators/test_materializer.py`
- Modify: `src/zenml/evaluators/__init__.py`

**Reference:** Look at an existing Pydantic-model materializer in `src/zenml/materializers/` to mirror the pattern (e.g., `pydantic_materializer.py` if present, or `built_in_materializer.py`):

```bash
ls /home/demian/Projects/zenml/src/zenml/materializers/
```

- [ ] **Step 1: Inspect an existing materializer**

Run: `ls /home/demian/Projects/zenml/src/zenml/materializers/ && grep -l "BaseMaterializer" /home/demian/Projects/zenml/src/zenml/materializers/*.py | head -3`

Open one (e.g., `pydantic_materializer.py`) to understand the `load` / `save` / `ASSOCIATED_TYPES` pattern. Mirror it.

- [ ] **Step 2: Write failing test**

Create `tests/unit/evaluators/test_materializer.py`:

```python
import os
import tempfile

from zenml.evaluators.materializer import EvaluationResultMaterializer
from zenml.evaluators.result import (
    CaseResult,
    EvaluationMode,
    EvaluationResult,
)


def _sample_result() -> EvaluationResult:
    return EvaluationResult(
        evaluator="openai",
        mode=EvaluationMode.RAG,
        suite_name="rag_quality",
        cases=[
            CaseResult(case_id="c1", scores={"f": 0.9}, passed=True),
        ],
        aggregates={"f_mean": 0.9, "pass_rate": 1.0},
        metadata={"model_version_id": "abc"},
    )


def test_materializer_round_trip():
    with tempfile.TemporaryDirectory() as tmp:
        m = EvaluationResultMaterializer(uri=tmp)
        original = _sample_result()
        m.save(original)
        loaded = m.load(EvaluationResult)
        assert loaded == original


def test_materializer_associated_types():
    assert EvaluationResult in EvaluationResultMaterializer.ASSOCIATED_TYPES
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/unit/evaluators/test_materializer.py -v`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 4: Implement `materializer.py`**

Create `src/zenml/evaluators/materializer.py`. Mirror the existing Pydantic materializer pattern; the skeleton is:

```python
"""Materializer for EvaluationResult artifacts."""

import os
from typing import ClassVar, Type

from zenml.enums import ArtifactType
from zenml.evaluators.result import EvaluationResult
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

DATA_FILENAME = "evaluation_result.json"


class EvaluationResultMaterializer(BaseMaterializer):
    """Persists EvaluationResult as JSON via Pydantic's model_dump_json."""

    ASSOCIATED_TYPES: ClassVar[tuple[type, ...]] = (EvaluationResult,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA

    def load(self, data_type: Type[EvaluationResult]) -> EvaluationResult:
        path = os.path.join(self.uri, DATA_FILENAME)
        with fileio.open(path, "r") as f:
            return EvaluationResult.model_validate_json(f.read())

    def save(self, data: EvaluationResult) -> None:
        path = os.path.join(self.uri, DATA_FILENAME)
        with fileio.open(path, "w") as f:
            f.write(data.model_dump_json())
```

If the existing materializer pattern uses different imports or `ArtifactType` values, mirror those exactly.

- [ ] **Step 5: Run tests**

Run: `pytest tests/unit/evaluators/test_materializer.py -v`

Expected: 2 passed.

- [ ] **Step 6: Format and commit**

```bash
bash scripts/format.sh
git add src/zenml/evaluators/materializer.py tests/unit/evaluators/test_materializer.py
git commit -m "$(cat <<'EOF'
Add EvaluationResultMaterializer

Persists EvaluationResult artifacts as JSON. Registered against the
EvaluationResult type so step outputs are auto-materialized when
returned from evaluator steps.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Custom exceptions

**Files:**
- Create: `src/zenml/evaluators/exceptions.py`
- Modify: `src/zenml/evaluators/__init__.py`

- [ ] **Step 1: Implement exceptions**

Create `src/zenml/evaluators/exceptions.py`:

```python
"""Exceptions raised by the evaluator framework."""

from zenml.evaluators.result import EvaluationMode


class EvaluationModeNotSupportedError(Exception):
    """Raised when a flavor doesn't implement a requested evaluation mode."""

    def __init__(self, flavor: str, mode: EvaluationMode) -> None:
        super().__init__(
            f"Evaluator flavor '{flavor}' does not support mode '{mode}'. "
            f"Switch to a flavor whose `supported_modes` includes "
            f"`EvaluationMode.{mode.name}`."
        )
        self.flavor = flavor
        self.mode = mode


class EvaluationRegressionError(Exception):
    """Raised when an evaluator regressed and on_regression='fail'."""

    def __init__(
        self,
        suite_name: str,
        regressed_metrics: dict[str, float],
    ) -> None:
        deltas = ", ".join(
            f"{m}: {d:+.3f}" for m, d in regressed_metrics.items()
        )
        super().__init__(
            f"Evaluation suite '{suite_name}' regressed against baseline. "
            f"Deltas: {deltas}"
        )
        self.suite_name = suite_name
        self.regressed_metrics = regressed_metrics
```

- [ ] **Step 2: Re-export**

Update `src/zenml/evaluators/__init__.py`:

```python
from zenml.evaluators.exceptions import (
    EvaluationModeNotSupportedError,
    EvaluationRegressionError,
)
```

…and add both to `__all__`.

- [ ] **Step 3: Quick smoke test**

Run: `python -c "from zenml.evaluators import EvaluationModeNotSupportedError, EvaluationRegressionError; print('ok')"`

Expected: `ok`.

- [ ] **Step 4: Format and commit**

```bash
bash scripts/format.sh
git add src/zenml/evaluators/exceptions.py src/zenml/evaluators/__init__.py
git commit -m "Add evaluator framework exceptions

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: `BaseEvaluator`, config, and flavor

**Files:**
- Create: `src/zenml/evaluators/base_evaluator.py`
- Create: `tests/unit/evaluators/test_base_evaluator.py`
- Modify: `src/zenml/evaluators/__init__.py`

**Reference:** `src/zenml/experiment_trackers/base_experiment_tracker.py` is the closest template — open it and mirror the imports / class hierarchy:

```bash
cat /home/demian/Projects/zenml/src/zenml/experiment_trackers/base_experiment_tracker.py
```

- [ ] **Step 1: Inspect the reference base class**

Run: `cat /home/demian/Projects/zenml/src/zenml/experiment_trackers/base_experiment_tracker.py`

Note: the imports for `StackComponent`, `StackComponentConfig`, `Flavor`, and the `FLAVOR` registration pattern.

- [ ] **Step 2: Write failing test**

Create `tests/unit/evaluators/test_base_evaluator.py`:

```python
import pytest

from zenml.evaluators.base_evaluator import (
    BaseEvaluator,
    BaseEvaluatorConfig,
    BaseEvaluatorFlavor,
)
from zenml.evaluators.cases import PointwiseCase, RAGCase, ReferenceCase, Rubric
from zenml.evaluators.exceptions import EvaluationModeNotSupportedError
from zenml.evaluators.result import (
    CaseResult,
    EvaluationMode,
    EvaluationResult,
)
from zenml.enums import StackComponentType


class _StubEvaluator(BaseEvaluator):
    """Test double exposing only POINTWISE."""

    @property
    def supported_modes(self) -> set[EvaluationMode]:
        return {EvaluationMode.POINTWISE}

    def evaluate_pointwise(self, cases, rubric):
        return EvaluationResult(
            evaluator="stub",
            mode=EvaluationMode.POINTWISE,
            suite_name="test",
            cases=[
                CaseResult(case_id=f"c{i}", scores={"score": 1.0}, passed=True)
                for i, _ in enumerate(cases)
            ],
            aggregates={"score_mean": 1.0, "pass_rate": 1.0},
            metadata={},
        )


def _stub_instance() -> _StubEvaluator:
    # The flavor/config plumbing is exercised in stack-integration tests;
    # for unit tests we instantiate directly with a minimal config.
    return _StubEvaluator(
        name="stub",
        id="00000000-0000-0000-0000-000000000001",
        config=BaseEvaluatorConfig(),
        flavor="stub",
        type=StackComponentType.EVALUATOR,
        user="00000000-0000-0000-0000-000000000002",
        project="00000000-0000-0000-0000-000000000003",
        created="2026-01-01T00:00:00",
        updated="2026-01-01T00:00:00",
    )


def test_default_methods_raise_for_unsupported_modes():
    ev = _stub_instance()
    with pytest.raises(EvaluationModeNotSupportedError) as exc:
        ev.evaluate_rag([RAGCase(query="q", context=[], response="r")], [])
    assert exc.value.mode == EvaluationMode.RAG

    with pytest.raises(EvaluationModeNotSupportedError):
        ev.evaluate_reference(
            [ReferenceCase(input="i", output="o", expected="e")], []
        )


def test_supported_mode_works():
    ev = _stub_instance()
    rubric = Rubric(name="r", criterion="ok?", scale=(1, 5))
    result = ev.evaluate_pointwise(
        [PointwiseCase(input="i", output="o")], rubric
    )
    assert result.cases[0].passed is True


def test_flavor_registration():
    f = BaseEvaluatorFlavor()
    assert f.type == StackComponentType.EVALUATOR
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/unit/evaluators/test_base_evaluator.py -v`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 4: Implement `base_evaluator.py`**

Create `src/zenml/evaluators/base_evaluator.py`:

```python
"""Base classes for evaluator stack components."""

from abc import abstractmethod
from typing import TYPE_CHECKING, Type

from zenml.enums import StackComponentType
from zenml.evaluators.cases import (
    PointwiseCase,
    RAGCase,
    ReferenceCase,
    Rubric,
)
from zenml.evaluators.exceptions import EvaluationModeNotSupportedError
from zenml.evaluators.result import EvaluationMode, EvaluationResult
from zenml.stack import Flavor, StackComponent, StackComponentConfig


class BaseEvaluatorConfig(StackComponentConfig):
    """Base config for all evaluator flavors.

    Concrete flavors extend this with their own fields (model name,
    API key references, concurrency, etc.).
    """


class BaseEvaluator(StackComponent):
    """Base class for all evaluator stack components.

    A flavor declares which evaluation modes it supports via
    `supported_modes` and overrides the matching `evaluate_*` methods.
    Calling an unsupported mode raises EvaluationModeNotSupportedError.
    """

    @property
    @abstractmethod
    def supported_modes(self) -> set[EvaluationMode]:
        """The eval modes this flavor implements."""

    def evaluate_pointwise(
        self,
        cases: list[PointwiseCase],
        rubric: Rubric,
    ) -> EvaluationResult:
        """Score each case against a rubric. Override in subclasses."""
        raise EvaluationModeNotSupportedError(
            self.flavor, EvaluationMode.POINTWISE
        )

    def evaluate_reference(
        self,
        cases: list[ReferenceCase],
        metrics: list[str],
    ) -> EvaluationResult:
        """Score each case against its expected output. Override in subclasses."""
        raise EvaluationModeNotSupportedError(
            self.flavor, EvaluationMode.REFERENCE
        )

    def evaluate_rag(
        self,
        cases: list[RAGCase],
        metrics: list[str],
    ) -> EvaluationResult:
        """Score RAG triples (query, context, response). Override in subclasses."""
        raise EvaluationModeNotSupportedError(
            self.flavor, EvaluationMode.RAG
        )


class BaseEvaluatorFlavor(Flavor):
    """Base flavor for evaluator stack components."""

    @property
    def type(self) -> StackComponentType:
        return StackComponentType.EVALUATOR

    @property
    def config_class(self) -> Type[BaseEvaluatorConfig]:
        return BaseEvaluatorConfig

    @property
    def implementation_class(self) -> Type[BaseEvaluator]:
        return BaseEvaluator
```

If the import path for `Flavor` / `StackComponent` / `StackComponentConfig` is different (verify with `grep -rn "class Flavor" /home/demian/Projects/zenml/src/zenml/stack/ | head -3`), use the discovered path.

- [ ] **Step 5: Re-export from package**

Update `src/zenml/evaluators/__init__.py`:

```python
from zenml.evaluators.base_evaluator import (
    BaseEvaluator,
    BaseEvaluatorConfig,
    BaseEvaluatorFlavor,
)
```

…and add to `__all__`.

- [ ] **Step 6: Run tests**

Run: `pytest tests/unit/evaluators/test_base_evaluator.py -v`

Expected: 3 passed.

If `_stub_instance()` fails because `StackComponent.__init__` requires fields not listed, open `src/zenml/stack/stack_component.py` and align the constructor args. The skeleton above lists the *common* required fields; adjust if needed.

- [ ] **Step 7: Format and commit**

```bash
bash scripts/format.sh
git add src/zenml/evaluators/base_evaluator.py src/zenml/evaluators/__init__.py tests/unit/evaluators/test_base_evaluator.py
git commit -m "$(cat <<'EOF'
Add BaseEvaluator, BaseEvaluatorConfig, BaseEvaluatorFlavor

Abstract base for the new evaluator stack component type. Default
evaluate_* implementations raise EvaluationModeNotSupportedError so
flavors can opt in to modes incrementally without boilerplate.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Baseline resolution

**Files:**
- Create: `src/zenml/evaluators/baseline.py`
- Create: `tests/unit/evaluators/test_baseline.py`

- [ ] **Step 1: Inspect the model registry API surface**

Run: `grep -rn "class BaseModelRegistry\|def list_model_versions\|def get_model_version" /home/demian/Projects/zenml/src/zenml/model_registries/ | head -10`

Goal: identify the method that fetches a model version's linked artifacts. Mirror its usage.

Also check the model–artifact linkage:

```bash
grep -rn "link_artifact\|get_artifacts_for_model\|model_version.*artifacts" /home/demian/Projects/zenml/src/zenml/client.py | head -10
```

If a clear API isn't visible, baseline resolution falls back to artifact tag lookup (described below).

- [ ] **Step 2: Write failing tests**

Create `tests/unit/evaluators/test_baseline.py`:

```python
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from zenml.evaluators.baseline import BaselineSpec, resolve_baseline
from zenml.evaluators.result import (
    CaseResult,
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/unit/evaluators/test_baseline.py -v`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 4: Implement `baseline.py`**

Create `src/zenml/evaluators/baseline.py`:

```python
"""Resolve a baseline EvaluationResult to compare against."""

from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.client import Client
from zenml.evaluators.result import EvaluationMode, EvaluationResult
from zenml.logger import get_logger

logger = get_logger(__name__)


BaselineStrategy = Literal["explicit", "model_registry", "none"]


class BaselineSpec(BaseModel):
    """How to resolve the baseline for a given evaluator run."""

    strategy: BaselineStrategy = "model_registry"
    artifact_id: Optional[UUID] = None
    run_id: Optional[UUID] = None
    model_version_id: Optional[UUID] = None  # override: pull from this version


def resolve_baseline(
    spec: BaselineSpec,
    suite_name: str,
    mode: EvaluationMode,
) -> Optional[EvaluationResult]:
    """Resolve the baseline EvaluationResult, or None if there isn't one.

    Strategies:
      - "explicit": fetch the EvaluationResult by artifact_id or run_id.
        Raises if neither is provided.
      - "model_registry": pull the latest EvaluationResult linked to the
        production model version, filtered by suite_name and mode. Returns
        None gracefully if no registry is configured or no production
        version exists.
      - "none": always returns None.

    Args:
        spec: Baseline configuration.
        suite_name: Logical join key for matching baseline to current.
        mode: Eval mode of the current run; baseline must match.

    Returns:
        The baseline EvaluationResult, or None.
    """
    if spec.strategy == "none":
        return None

    if spec.strategy == "explicit":
        return _resolve_explicit(spec)

    if spec.strategy == "model_registry":
        return _resolve_from_model_registry(spec, suite_name, mode)

    raise ValueError(f"Unknown baseline strategy: {spec.strategy}")


def _resolve_explicit(spec: BaselineSpec) -> EvaluationResult:
    if spec.artifact_id is None and spec.run_id is None:
        raise ValueError(
            "Explicit baseline requires artifact_id or run_id."
        )
    client = Client()
    if spec.artifact_id is not None:
        artifact = client.get_artifact_version(spec.artifact_id)
        return artifact.load(EvaluationResult)
    # run_id path: fetch the run, find the EvaluationResult output.
    raise NotImplementedError(
        "Resolving baseline by run_id is not yet supported. "
        "Pass artifact_id instead."
    )


def _resolve_from_model_registry(
    spec: BaselineSpec,
    suite_name: str,
    mode: EvaluationMode,
) -> Optional[EvaluationResult]:
    client = Client()
    registry = client.get_active_stack().model_registry
    if registry is None:
        logger.debug(
            "No model_registry in active stack; baseline=None "
            "(strategy=model_registry)."
        )
        return None

    # Implementation note: the exact API to fetch the production model
    # version + its linked EvaluationResult depends on the model registry
    # interface. Pseudocode:
    #
    #   prod_version = registry.get_production_version(...)
    #   linked_results = client.list_artifact_versions(
    #       model_version_id=prod_version.id,
    #       data_type=EvaluationResult,
    #   )
    #   matching = [
    #       r for r in linked_results
    #       if r.suite_name == suite_name and r.mode == mode
    #   ]
    #   return matching[0] if matching else None
    #
    # Verify exact method names against src/zenml/model_registries/
    # base_model_registry.py and src/zenml/client.py during implementation.
    logger.warning(
        "Model-registry baseline resolution is stubbed. Returning None. "
        "Wire up against the active model registry API."
    )
    return None
```

The `_resolve_from_model_registry` body is intentionally a stub with a clear extension point. The "wire up against the model registry API" work is captured as Task 7b below.

- [ ] **Step 5: Run tests**

Run: `pytest tests/unit/evaluators/test_baseline.py -v`

Expected: 4 passed.

- [ ] **Step 6: Format and commit**

```bash
bash scripts/format.sh
git add src/zenml/evaluators/baseline.py tests/unit/evaluators/test_baseline.py
git commit -m "$(cat <<'EOF'
Add baseline resolution scaffolding

Three strategies: explicit (by artifact_id), model_registry (default,
stubbed), and none. Model-registry path returns None gracefully when
no registry is configured; full wiring follows in Task 7b.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7b: Wire model-registry baseline resolution

**Files:**
- Modify: `src/zenml/evaluators/baseline.py` — `_resolve_from_model_registry`
- Modify: `tests/unit/evaluators/test_baseline.py`

- [ ] **Step 1: Locate the production-version + linked-artifacts API**

Run:

```bash
grep -rn "production\|stage.*production\|list_model_versions" /home/demian/Projects/zenml/src/zenml/model_registries/base_model_registry.py
grep -rn "list_artifact_versions\|model_version_id" /home/demian/Projects/zenml/src/zenml/client.py | head -10
```

Document the exact calls in a comment at the top of `_resolve_from_model_registry` before implementing.

- [ ] **Step 2: Write the failing integration test**

Add to `tests/unit/evaluators/test_baseline.py`:

```python
def test_resolve_baseline_model_registry_with_production(monkeypatch):
    fake_result = _result("s", EvaluationMode.RAG, {"f": 0.85})
    fake_artifact = MagicMock(load=MagicMock(return_value=fake_result))
    fake_client = MagicMock()

    # Stack has a model registry with a production version.
    fake_registry = MagicMock()
    fake_version = MagicMock(id=uuid4())
    fake_registry.get_production_version.return_value = fake_version
    fake_client.get_active_stack.return_value.model_registry = fake_registry

    # Client returns one matching EvaluationResult linked to that version.
    fake_artifact.metadata = {"suite_name": "s", "mode": EvaluationMode.RAG}
    fake_client.list_artifact_versions.return_value = [fake_artifact]
    monkeypatch.setattr(
        "zenml.evaluators.baseline.Client", lambda: fake_client
    )

    out = resolve_baseline(
        BaselineSpec(strategy="model_registry"),
        suite_name="s",
        mode=EvaluationMode.RAG,
    )
    assert out == fake_result
```

- [ ] **Step 3: Run to confirm fail**

Run: `pytest tests/unit/evaluators/test_baseline.py::test_resolve_baseline_model_registry_with_production -v`

Expected: FAIL — current stub returns None.

- [ ] **Step 4: Implement against the actual API**

Replace `_resolve_from_model_registry` with the real implementation, using the API surface discovered in Step 1. Filter `list_artifact_versions` by `data_type=EvaluationResult` and `model_version_id=prod_version.id`, then filter the loaded results by `suite_name` and `mode`. Return the most recent match (sorted by created-at) or None.

- [ ] **Step 5: Run tests**

Run: `pytest tests/unit/evaluators/test_baseline.py -v`

Expected: 5 passed.

- [ ] **Step 6: Format and commit**

```bash
bash scripts/format.sh
git add src/zenml/evaluators/baseline.py tests/unit/evaluators/test_baseline.py
git commit -m "Wire model-registry baseline resolution

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: `EvalRegression` event integration

**Files:**
- Create: `src/zenml/evaluators/events.py`
- Create: `tests/unit/evaluators/test_events.py`
- Modify: registration call site (location TBD in step 1)

- [ ] **Step 1: Locate event-trigger system entry points**

The recent event-trigger work landed in commits `2c84f7108` (Feature/event triggers), `2b5813584` (helper endpoint), `d81c9d724` (acknowledgeable trigger dispatch). Find the relevant modules:

```bash
grep -rn "class BaseEvent\|class EventSource\|register_event\|EVENT_SOURCE_REGISTRY" /home/demian/Projects/zenml/src/zenml/ | head -20
git log --oneline --all -- "*/events/*" "*event_source*" "*event_hub*" | head -20
```

Identify:
- The base class for events (e.g., `BaseEvent`).
- How a new event type is registered.
- How an event is *emitted* (what API does an emitter call?).

Document the answers at the top of `events.py` before implementing.

- [ ] **Step 2: Write failing test**

Create `tests/unit/evaluators/test_events.py`:

```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/unit/evaluators/test_events.py -v`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 4: Implement `events.py`**

Create `src/zenml/evaluators/events.py`. The skeleton (subclass the discovered base; if no `BaseEvent` exists yet, use a plain Pydantic model):

```python
"""Event types emitted by the evaluator framework."""

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from zenml.evaluators.result import EvaluationMode

# Subclass the project's BaseEvent if available; otherwise BaseModel
# is fine and the trigger system can wrap it.


class EvalRegressionEvent(BaseModel):
    """Emitted when an evaluator run regresses against its baseline."""

    suite_name: str
    mode: EvaluationMode
    evaluator: str
    pipeline_run_id: UUID
    artifact_id: UUID
    aggregates: dict[str, float]
    baseline_aggregates: dict[str, float]
    regressed_metrics: dict[str, float]  # metric -> delta (negative = worse)
    model_version_id: Optional[UUID] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 5: Register the event type (if registry exists)**

If the discovery in Step 1 found an `EVENT_SOURCE_REGISTRY` (or similar): add registration in `events.py`:

```python
# At module load:
# from zenml.event_sources import EVENT_SOURCE_REGISTRY
# EVENT_SOURCE_REGISTRY.register("eval_regression", EvalRegressionEvent)
```

If no such registry exists yet, leave the event class defined and emit it directly from the step body in Task 9 — registration can land later as part of trigger-system follow-up.

- [ ] **Step 6: Run tests**

Run: `pytest tests/unit/evaluators/test_events.py -v`

Expected: 1 passed.

- [ ] **Step 7: Format and commit**

```bash
bash scripts/format.sh
git add src/zenml/evaluators/events.py tests/unit/evaluators/test_events.py
git commit -m "$(cat <<'EOF'
Add EvalRegressionEvent for evaluator-trigger integration

Carries baseline + current aggregates and the regression delta so
trigger handlers can route alerts (Slack, PagerDuty, follow-up runs)
based on severity.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Pre-built evaluator step functions

**Files:**
- Create: `src/zenml/evaluators/steps.py`
- Create: `tests/unit/evaluators/test_steps.py`
- Modify: `src/zenml/evaluators/__init__.py`

This is the central pipeline-facing API. The step bodies orchestrate: resolve evaluator → call mode → compute pass/fail → resolve baseline → compute regression → apply gate → return artifact.

- [ ] **Step 1: Write failing tests for step orchestration**

Create `tests/unit/evaluators/test_steps.py`:

```python
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from zenml.evaluators.cases import PointwiseCase, RAGCase, ReferenceCase, Rubric
from zenml.evaluators.exceptions import EvaluationRegressionError
from zenml.evaluators.result import (
    CaseResult,
    EvaluationMode,
    EvaluationResult,
)
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
    # No thresholds → all pass.
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
    assert _compute_regressed_metrics(
        current={"f_mean": 0.8}, baseline=None, tolerance=0.0
    ) == {}


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/evaluators/test_steps.py -v`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `steps.py`**

Create `src/zenml/evaluators/steps.py`:

```python
"""Pre-built ZenML steps that invoke the active stack's evaluator."""

import statistics
from typing import Any, Literal, Optional
from uuid import UUID

from zenml import step
from zenml.client import Client
from zenml.evaluators.baseline import BaselineSpec, resolve_baseline
from zenml.evaluators.cases import (
    PointwiseCase,
    RAGCase,
    ReferenceCase,
    Rubric,
)
from zenml.evaluators.events import EvalRegressionEvent
from zenml.evaluators.exceptions import EvaluationRegressionError
from zenml.evaluators.result import (
    CaseResult,
    EvaluationMode,
    EvaluationResult,
)
from zenml.logger import get_logger

logger = get_logger(__name__)

OnRegression = Literal["fail", "warn", "trigger"]


def _compute_aggregates(cases: list[CaseResult]) -> dict[str, float]:
    """Mean per metric and overall pass_rate."""
    if not cases:
        return {"pass_rate": 0.0}
    metric_names = set()
    for c in cases:
        metric_names.update(c.scores.keys())
    agg: dict[str, float] = {}
    for m in metric_names:
        values = [c.scores[m] for c in cases if m in c.scores]
        if values:
            agg[f"{m}_mean"] = statistics.fmean(values)
    agg["pass_rate"] = sum(1 for c in cases if c.passed) / len(cases)
    return agg


def _mark_passed(
    cases: list[CaseResult],
    pass_thresholds: Optional[dict[str, float]],
) -> list[CaseResult]:
    """Return cases with `passed` recomputed against the supplied thresholds.

    If no thresholds are supplied, every case is considered passed.
    """
    if not pass_thresholds:
        return [c.model_copy(update={"passed": True}) for c in cases]

    out: list[CaseResult] = []
    for c in cases:
        ok = all(
            c.scores.get(m, float("-inf")) >= thr
            for m, thr in pass_thresholds.items()
        )
        out.append(c.model_copy(update={"passed": ok}))
    return out


def _compute_regressed_metrics(
    current: dict[str, float],
    baseline: Optional[dict[str, float]],
    tolerance: float,
) -> dict[str, float]:
    """Return metric -> delta for metrics that regressed beyond tolerance.

    Delta is negative (current - baseline). Tolerance is the maximum
    absolute drop that's still considered acceptable.
    """
    if not baseline:
        return {}
    regressed: dict[str, float] = {}
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
    regressed_metrics: dict[str, float],
    event_payload: dict[str, Any],
) -> None:
    """Apply the configured gate behavior. No-op if no regression."""
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


def _emit_event(payload: dict[str, Any]) -> None:
    """Emit an EvalRegression event to the trigger system.

    Implementation depends on the discovered event-trigger API (see Task 8).
    For now, log; replace with the registered emitter once known.
    """
    logger.info("EvalRegression event payload: %s", payload)
    # TODO(Task 8 follow-up): call the actual event emitter.


def _execute(
    mode: EvaluationMode,
    invoke,
    suite_name: str,
    baseline: BaselineSpec,
    on_regression: OnRegression,
    pass_thresholds: Optional[dict[str, float]],
    regression_tolerance: float,
) -> EvaluationResult:
    """Shared body for the three evaluate_* steps."""
    client = Client()
    evaluator = client.active_stack.evaluator  # may raise if unconfigured
    if mode not in evaluator.supported_modes:
        from zenml.evaluators.exceptions import (
            EvaluationModeNotSupportedError,
        )
        raise EvaluationModeNotSupportedError(evaluator.flavor, mode)

    raw_result = invoke(evaluator)
    cases = _mark_passed(raw_result.cases, pass_thresholds)
    aggregates = _compute_aggregates(cases)
    raw_result = raw_result.model_copy(
        update={"cases": cases, "aggregates": aggregates}
    )

    base_result = resolve_baseline(baseline, suite_name, mode)
    regressed = _compute_regressed_metrics(
        aggregates,
        base_result.aggregates if base_result else None,
        regression_tolerance,
    )
    if regressed:
        # Attach a flag so the artifact carries the verdict regardless of gate.
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
        "mode": mode,
        "evaluator": evaluator.flavor,
        "aggregates": aggregates,
        "baseline_aggregates": base_result.aggregates if base_result else {},
        "regressed_metrics": regressed,
    }
    _apply_gate(on_regression, suite_name, regressed, payload)
    return raw_result


@step
def evaluate_pointwise(
    cases: list[PointwiseCase],
    rubric: Rubric,
    suite_name: str,
    baseline: BaselineSpec = BaselineSpec(strategy="model_registry"),
    on_regression: OnRegression = "trigger",
    pass_thresholds: Optional[dict[str, float]] = None,
    regression_tolerance: float = 0.0,
) -> EvaluationResult:
    """Run pointwise eval and gate the run on regression."""
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
    cases: list[ReferenceCase],
    metrics: list[str],
    suite_name: str,
    baseline: BaselineSpec = BaselineSpec(strategy="model_registry"),
    on_regression: OnRegression = "trigger",
    pass_thresholds: Optional[dict[str, float]] = None,
    regression_tolerance: float = 0.0,
) -> EvaluationResult:
    """Run reference-based eval and gate the run on regression."""
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
    cases: list[RAGCase],
    metrics: list[str],
    suite_name: str,
    baseline: BaselineSpec = BaselineSpec(strategy="model_registry"),
    on_regression: OnRegression = "trigger",
    pass_thresholds: Optional[dict[str, float]] = None,
    regression_tolerance: float = 0.0,
) -> EvaluationResult:
    """Run RAG eval and gate the run on regression."""
    return _execute(
        mode=EvaluationMode.RAG,
        invoke=lambda ev: ev.evaluate_rag(cases, metrics),
        suite_name=suite_name,
        baseline=baseline,
        on_regression=on_regression,
        pass_thresholds=pass_thresholds,
        regression_tolerance=regression_tolerance,
    )
```

- [ ] **Step 4: Re-export from package**

Update `src/zenml/evaluators/__init__.py`:

```python
from zenml.evaluators.baseline import BaselineSpec
from zenml.evaluators.steps import (
    evaluate_pointwise,
    evaluate_reference,
    evaluate_rag,
)
```

…and add all to `__all__`.

- [ ] **Step 5: Run tests**

Run: `pytest tests/unit/evaluators/test_steps.py -v`

Expected: 11 passed.

- [ ] **Step 6: Format and commit**

```bash
bash scripts/format.sh
git add src/zenml/evaluators/steps.py src/zenml/evaluators/__init__.py tests/unit/evaluators/test_steps.py
git commit -m "$(cat <<'EOF'
Add evaluate_pointwise/reference/rag steps

Pipeline-facing API: pre-built ZenML steps that resolve the active
stack's evaluator, compute per-case pass/fail and aggregates, fetch
the configured baseline, and apply the gate (fail/warn/trigger).

Pure helpers (_compute_aggregates, _mark_passed,
_compute_regressed_metrics, _apply_gate) are unit-tested in isolation.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Wire `evaluator` into `Stack`

**Files:**
- Modify: `src/zenml/stack/stack.py` (verify exact path during Step 1)
- Modify: tests covering Stack composition (locate during step 1)

ZenML's `Stack` class holds typed slots for each component (e.g., `experiment_tracker`, `model_registry`). Add an `evaluator` slot.

- [ ] **Step 1: Locate the Stack class**

Run:

```bash
grep -rn "class Stack" /home/demian/Projects/zenml/src/zenml/stack/ | head -5
grep -rn "experiment_tracker.*BaseExperimentTracker" /home/demian/Projects/zenml/src/zenml/stack/stack.py
```

Open the file and find where `experiment_tracker` and `model_registry` are declared as optional `Optional[BaseX]` properties. Mirror that exactly for `evaluator`.

- [ ] **Step 2: Write failing test**

Locate or create a Stack composition test (e.g., `tests/unit/stack/test_stack.py`). Add:

```python
def test_stack_has_optional_evaluator(stack_with_components_factory):
    # Use whatever fixture/builder the existing stack tests use.
    stack = stack_with_components_factory()
    # Default: no evaluator configured → property returns None.
    assert stack.evaluator is None
```

If no such fixture exists, mirror the assertion style used by other Stack tests (look at how `experiment_tracker` is tested).

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest <discovered_test_path> -v -k evaluator`

Expected: FAIL — Stack has no `evaluator` attribute.

- [ ] **Step 4: Add the slot**

In `src/zenml/stack/stack.py`, locate the block where `experiment_tracker` is declared and add a parallel `evaluator` slot. Mirror:
- The constructor parameter (`Optional[BaseEvaluator] = None`).
- The `@property` accessor.
- Any internal lookup table that maps `StackComponentType` → component (e.g., `_components` dict). If such a table exists and is exhaustive, add the new mapping.
- Imports: `from zenml.evaluators.base_evaluator import BaseEvaluator` (use `TYPE_CHECKING` guard if the file does so for other component types).

Verify by grepping for `experiment_tracker` in the file and replicating each occurrence at the same point of the class for `evaluator`.

- [ ] **Step 5: Run tests**

Run: `pytest <discovered_test_path> -v`

Expected: stack tests green.

Run also: `pytest tests/unit/evaluators/ -v`

Expected: still all green.

- [ ] **Step 6: Format and commit**

```bash
bash scripts/format.sh
git add src/zenml/stack/stack.py tests/
git commit -m "$(cat <<'EOF'
Wire evaluator slot into Stack

Adds an optional evaluator component to the Stack, parallel to
experiment_tracker. Pipelines that use evaluate_* steps without an
evaluator configured fail at pipeline-build time with a clear message.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Decide on Alembic migration

**Files:**
- Possibly create: `src/zenml/zen_stores/migrations/versions/<hash>_add_evaluator_component_type.py`

- [ ] **Step 1: Determine if a migration is needed**

Check whether the `stack_component.type` column is a SQL enum or a free-text string:

```bash
grep -rn "class StackComponentSchema\|type.*Column\|type.*Field" /home/demian/Projects/zenml/src/zenml/zen_stores/schemas/component_schemas.py 2>/dev/null
grep -rn "stack_component" /home/demian/Projects/zenml/src/zenml/zen_stores/schemas/ | head -5
```

- If the column is `String(...)` / `VARCHAR` and the enum is enforced at the application layer only: **no migration needed**. Skip to Task 12.
- If the column is a SQL ENUM type: a migration is needed.

- [ ] **Step 2 (only if needed): Generate migration**

```bash
cd /home/demian/Projects/zenml
alembic -c src/zenml/zen_stores/migrations/alembic.ini revision -m "Add evaluator component type"
```

Edit the generated file to add `evaluator` to the enum. Pattern from a recent migration (use one as a reference):

```bash
ls src/zenml/zen_stores/migrations/versions/ | tail -5
```

- [ ] **Step 3: Test upgrade**

```bash
alembic -c src/zenml/zen_stores/migrations/alembic.ini upgrade head
```

Expected: applies cleanly. Run `bash scripts/check-alembic-branches.sh` to ensure no branching.

- [ ] **Step 4: Commit**

```bash
git add src/zenml/zen_stores/migrations/
git commit -m "Add Alembic migration for evaluator component type

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 12: `OpenAIEvaluator` flavor

**Files:**
- Create: `src/zenml/integrations/openai/evaluators/__init__.py`
- Create: `src/zenml/integrations/openai/evaluators/openai_evaluator.py`
- Create: `src/zenml/integrations/openai/evaluators/openai_evaluator_flavor.py`
- Modify: `src/zenml/integrations/openai/__init__.py` (register flavor)
- Create: `tests/unit/integrations/openai/test_openai_evaluator.py`

**Reference:** mirror `experiment_tracker` flavors in `src/zenml/integrations/`. Find a small one to use as template:

```bash
ls /home/demian/Projects/zenml/src/zenml/integrations/openai/
grep -rn "ExperimentTrackerFlavor\|TrackerFlavor" /home/demian/Projects/zenml/src/zenml/integrations/wandb/ 2>/dev/null | head -10
```

- [ ] **Step 1: Inspect the openai integration entry point**

Run: `cat /home/demian/Projects/zenml/src/zenml/integrations/openai/__init__.py`

Note how flavors / hooks register on import.

- [ ] **Step 2: Write failing test**

Create `tests/unit/integrations/openai/test_openai_evaluator.py`:

```python
from unittest.mock import MagicMock, patch

from zenml.evaluators.cases import PointwiseCase, RAGCase, Rubric
from zenml.evaluators.result import EvaluationMode
from zenml.integrations.openai.evaluators.openai_evaluator import (
    OpenAIEvaluator,
)
from zenml.integrations.openai.evaluators.openai_evaluator_flavor import (
    OpenAIEvaluatorConfig,
    OpenAIEvaluatorFlavor,
)


def test_supported_modes_includes_all_three():
    config = OpenAIEvaluatorConfig(model="gpt-4o-mini")
    ev = OpenAIEvaluator.__new__(OpenAIEvaluator)
    ev._config = config  # type: ignore[attr-defined]
    assert {
        EvaluationMode.POINTWISE,
        EvaluationMode.REFERENCE,
        EvaluationMode.RAG,
    } <= ev.supported_modes


def test_flavor_metadata():
    f = OpenAIEvaluatorFlavor()
    assert f.name == "openai"
    assert f.config_class is OpenAIEvaluatorConfig
    assert f.implementation_class is OpenAIEvaluator


def test_pointwise_calls_openai_with_rubric(monkeypatch):
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"score": 4}'))]
    )
    monkeypatch.setattr(
        "zenml.integrations.openai.evaluators.openai_evaluator._openai_client",
        lambda cfg: fake_client,
    )
    config = OpenAIEvaluatorConfig(model="gpt-4o-mini")
    ev = OpenAIEvaluator.__new__(OpenAIEvaluator)
    ev._config = config  # type: ignore[attr-defined]

    rubric = Rubric(name="r", criterion="ok?", scale=(1, 5))
    result = ev.evaluate_pointwise(
        [PointwiseCase(input="i", output="o")], rubric
    )
    assert len(result.cases) == 1
    assert result.cases[0].scores["score"] == 4
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/unit/integrations/openai/test_openai_evaluator.py -v`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 4: Implement the flavor**

Create `src/zenml/integrations/openai/evaluators/__init__.py`:

```python
"""OpenAI-backed implementation of the evaluator stack component."""

from zenml.integrations.openai.evaluators.openai_evaluator import (
    OpenAIEvaluator,
)
from zenml.integrations.openai.evaluators.openai_evaluator_flavor import (
    OpenAIEvaluatorConfig,
    OpenAIEvaluatorFlavor,
)

__all__ = [
    "OpenAIEvaluator",
    "OpenAIEvaluatorConfig",
    "OpenAIEvaluatorFlavor",
]
```

Create `src/zenml/integrations/openai/evaluators/openai_evaluator_flavor.py`:

```python
"""Config and Flavor for OpenAIEvaluator."""

from typing import TYPE_CHECKING, Optional, Type

from pydantic import Field

from zenml.evaluators.base_evaluator import (
    BaseEvaluatorConfig,
    BaseEvaluatorFlavor,
)

if TYPE_CHECKING:
    from zenml.integrations.openai.evaluators.openai_evaluator import (
        OpenAIEvaluator,
    )


OPENAI_EVALUATOR_FLAVOR = "openai"


class OpenAIEvaluatorConfig(BaseEvaluatorConfig):
    """Config for the OpenAI-backed evaluator."""

    model: str = Field(
        "gpt-4o-mini",
        description=(
            "OpenAI chat model used as judge. Must support structured "
            "JSON output (response_format). Examples: 'gpt-4o', "
            "'gpt-4o-mini'. Defaults to gpt-4o-mini for cost"
        ),
    )
    temperature: float = Field(
        0.0,
        description=(
            "Sampling temperature for the judge. 0.0 minimizes variance "
            "and is recommended for reproducible eval"
        ),
    )
    max_concurrency: int = Field(
        4,
        description=(
            "Max concurrent requests to OpenAI when evaluating multiple "
            "cases in parallel. Default 4"
        ),
    )
    api_key_secret: Optional[str] = Field(
        None,
        description=(
            "ZenML secret reference holding OPENAI_API_KEY. If unset, "
            "falls back to the OPENAI_API_KEY environment variable"
        ),
    )


class OpenAIEvaluatorFlavor(BaseEvaluatorFlavor):
    """Flavor metadata for OpenAIEvaluator."""

    @property
    def name(self) -> str:
        return OPENAI_EVALUATOR_FLAVOR

    @property
    def config_class(self) -> Type[OpenAIEvaluatorConfig]:
        return OpenAIEvaluatorConfig

    @property
    def implementation_class(self) -> Type["OpenAIEvaluator"]:
        from zenml.integrations.openai.evaluators.openai_evaluator import (
            OpenAIEvaluator,
        )
        return OpenAIEvaluator
```

Create `src/zenml/integrations/openai/evaluators/openai_evaluator.py`:

```python
"""OpenAI-backed evaluator: LLM-as-judge across all three v1 modes."""

import json
from typing import Any

from zenml.evaluators.base_evaluator import BaseEvaluator
from zenml.evaluators.cases import (
    PointwiseCase,
    RAGCase,
    ReferenceCase,
    Rubric,
)
from zenml.evaluators.result import (
    CaseResult,
    EvaluationMode,
    EvaluationResult,
)
from zenml.integrations.openai.evaluators.openai_evaluator_flavor import (
    OPENAI_EVALUATOR_FLAVOR,
    OpenAIEvaluatorConfig,
)


def _openai_client(config: OpenAIEvaluatorConfig):
    """Return a configured OpenAI client. Imported lazily to avoid
    pulling the openai dependency on flavor-registration."""
    from openai import OpenAI

    if config.api_key_secret:
        from zenml.client import Client as ZenClient

        secret = ZenClient().get_secret(config.api_key_secret)
        api_key = secret.values["OPENAI_API_KEY"]
        return OpenAI(api_key=api_key)
    return OpenAI()  # falls back to env var


class OpenAIEvaluator(BaseEvaluator):
    """LLM-as-judge evaluator backed by an OpenAI chat model."""

    @property
    def config(self) -> OpenAIEvaluatorConfig:
        return self._config  # type: ignore[return-value]

    @property
    def supported_modes(self) -> set[EvaluationMode]:
        return {
            EvaluationMode.POINTWISE,
            EvaluationMode.REFERENCE,
            EvaluationMode.RAG,
        }

    # --- Pointwise -------------------------------------------------

    def evaluate_pointwise(
        self,
        cases: list[PointwiseCase],
        rubric: Rubric,
    ) -> EvaluationResult:
        client = _openai_client(self.config)
        cases_out: list[CaseResult] = []
        for i, case in enumerate(cases):
            score, raw = self._judge_pointwise(client, case, rubric)
            cases_out.append(
                CaseResult(
                    case_id=str(i),
                    scores={"score": float(score)},
                    passed=True,  # threshold applied later in the step
                    raw=raw,
                )
            )
        return EvaluationResult(
            evaluator=OPENAI_EVALUATOR_FLAVOR,
            mode=EvaluationMode.POINTWISE,
            suite_name="",  # set by the step wrapper
            cases=cases_out,
            aggregates={},  # recomputed in the step wrapper
            metadata={"model": self.config.model},
        )

    def _judge_pointwise(
        self,
        client,
        case: PointwiseCase,
        rubric: Rubric,
    ) -> tuple[int, dict[str, Any]]:
        lo, hi = rubric.scale
        prompt = (
            f"You are evaluating the following output against this rubric.\n"
            f"Rubric: {rubric.criterion}\n"
            f"Score on a scale from {lo} to {hi}.\n"
            f"Input: {case.input}\nOutput: {case.output}\n"
            f"Reply with strict JSON: {{\"score\": <int>}}"
        )
        resp = client.chat.completions.create(
            model=self.config.model,
            temperature=self.config.temperature,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        content = resp.choices[0].message.content
        parsed = json.loads(content)
        return parsed["score"], parsed

    # --- Reference -------------------------------------------------

    def evaluate_reference(
        self,
        cases: list[ReferenceCase],
        metrics: list[str],
    ) -> EvaluationResult:
        # Default metric: semantic equivalence judged by LLM.
        # `metrics` is reserved for future per-metric routing.
        client = _openai_client(self.config)
        cases_out: list[CaseResult] = []
        for i, case in enumerate(cases):
            equiv, raw = self._judge_reference(client, case)
            cases_out.append(
                CaseResult(
                    case_id=str(i),
                    scores={"equivalence": 1.0 if equiv else 0.0},
                    passed=True,
                    raw=raw,
                )
            )
        return EvaluationResult(
            evaluator=OPENAI_EVALUATOR_FLAVOR,
            mode=EvaluationMode.REFERENCE,
            suite_name="",
            cases=cases_out,
            aggregates={},
            metadata={"model": self.config.model, "metrics": metrics},
        )

    def _judge_reference(
        self, client, case: ReferenceCase
    ) -> tuple[bool, dict[str, Any]]:
        prompt = (
            f"Are these two outputs semantically equivalent?\n"
            f"Expected: {case.expected}\nActual: {case.output}\n"
            f"Reply with strict JSON: {{\"equivalent\": <true|false>}}"
        )
        resp = client.chat.completions.create(
            model=self.config.model,
            temperature=self.config.temperature,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        parsed = json.loads(resp.choices[0].message.content)
        return bool(parsed["equivalent"]), parsed

    # --- RAG -------------------------------------------------------

    def evaluate_rag(
        self,
        cases: list[RAGCase],
        metrics: list[str],
    ) -> EvaluationResult:
        client = _openai_client(self.config)
        cases_out: list[CaseResult] = []
        for i, case in enumerate(cases):
            scores, raw = self._judge_rag(client, case, metrics)
            cases_out.append(
                CaseResult(
                    case_id=str(i),
                    scores=scores,
                    passed=True,
                    raw=raw,
                )
            )
        return EvaluationResult(
            evaluator=OPENAI_EVALUATOR_FLAVOR,
            mode=EvaluationMode.RAG,
            suite_name="",
            cases=cases_out,
            aggregates={},
            metadata={"model": self.config.model, "metrics": metrics},
        )

    def _judge_rag(
        self,
        client,
        case: RAGCase,
        metrics: list[str],
    ) -> tuple[dict[str, float], dict[str, Any]]:
        prompt = (
            "You are evaluating a retrieval-augmented response. "
            "Score each metric in [0.0, 1.0]:\n"
            f"Metrics: {metrics}\n"
            f"Query: {case.query}\n"
            f"Context: {case.context}\nResponse: {case.response}\n"
            "Reply with strict JSON: {\"<metric>\": <float>, ...}"
        )
        resp = client.chat.completions.create(
            model=self.config.model,
            temperature=self.config.temperature,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        parsed = json.loads(resp.choices[0].message.content)
        scores = {m: float(parsed[m]) for m in metrics if m in parsed}
        return scores, parsed
```

- [ ] **Step 5: Register the flavor on integration import**

Open `src/zenml/integrations/openai/__init__.py`. Find where existing flavors/hooks register. Add a corresponding registration call for `OpenAIEvaluatorFlavor`. Pattern (verify against the file's existing style):

```python
from zenml.integrations.openai.evaluators import OpenAIEvaluatorFlavor

# In whatever .flavors() / register loop the file uses:
@classmethod
def flavors(cls):
    return [..., OpenAIEvaluatorFlavor]
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/unit/integrations/openai/test_openai_evaluator.py -v`

Expected: 3 passed.

- [ ] **Step 7: Format and commit**

```bash
bash scripts/format.sh
git add src/zenml/integrations/openai/ tests/unit/integrations/openai/
git commit -m "$(cat <<'EOF'
Add OpenAIEvaluator flavor

LLM-as-judge implementation of the evaluator component supporting
all three v1 modes (pointwise, reference, RAG). Uses
response_format=json_object for stable judge output. API key resolves
via ZenML secret reference or OPENAI_API_KEY env var.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: `RagasEvaluator` flavor (new integration package)

**Files:**
- Create: `src/zenml/integrations/ragas/__init__.py`
- Create: `src/zenml/integrations/ragas/evaluators/__init__.py`
- Create: `src/zenml/integrations/ragas/evaluators/ragas_evaluator.py`
- Create: `src/zenml/integrations/ragas/evaluators/ragas_evaluator_flavor.py`
- Modify: integration registration (location TBD in step 1)
- Modify: `pyproject.toml` (add `ragas` extras)
- Create: `tests/unit/integrations/ragas/test_ragas_evaluator.py`

**Reference:** mirror a small recently-added integration package — `argilla` or `lightning` are reasonable templates:

```bash
ls /home/demian/Projects/zenml/src/zenml/integrations/argilla/
cat /home/demian/Projects/zenml/src/zenml/integrations/argilla/__init__.py
```

- [ ] **Step 1: Locate integration registration**

Run:

```bash
grep -rn "INTEGRATIONS_REGISTRY\|register_integration\|class.*Integration" /home/demian/Projects/zenml/src/zenml/integrations/ | head -20
```

Identify the pattern: each integration `__init__.py` declares an `Integration` subclass with `NAME`, `REQUIREMENTS`, and a `flavors()` classmethod that returns the flavor classes.

- [ ] **Step 2: Write failing test**

Create `tests/unit/integrations/ragas/test_ragas_evaluator.py`:

```python
from zenml.evaluators.result import EvaluationMode
from zenml.integrations.ragas.evaluators.ragas_evaluator_flavor import (
    RagasEvaluatorConfig,
    RagasEvaluatorFlavor,
)


def test_flavor_metadata():
    f = RagasEvaluatorFlavor()
    assert f.name == "ragas"


def test_supported_modes_excludes_pointwise():
    from zenml.integrations.ragas.evaluators.ragas_evaluator import (
        RagasEvaluator,
    )

    config = RagasEvaluatorConfig()
    ev = RagasEvaluator.__new__(RagasEvaluator)
    ev._config = config  # type: ignore[attr-defined]
    assert EvaluationMode.RAG in ev.supported_modes
    assert EvaluationMode.REFERENCE in ev.supported_modes
    assert EvaluationMode.POINTWISE not in ev.supported_modes
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/unit/integrations/ragas/test_ragas_evaluator.py -v`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 4: Implement the integration package**

Create `src/zenml/integrations/ragas/__init__.py` (mirror `argilla` pattern; verify `Integration` import path):

```python
"""Ragas integration: RAG-specific eval as a stack component flavor."""

from typing import List, Type

from zenml.integrations.constants import RAGAS  # add to constants.py if missing
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

RAGAS_EVALUATOR_FLAVOR = "ragas"


class RagasIntegration(Integration):
    NAME = RAGAS
    REQUIREMENTS = ["ragas>=0.2,<0.4"]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        from zenml.integrations.ragas.evaluators import RagasEvaluatorFlavor

        return [RagasEvaluatorFlavor]


RagasIntegration.check_installation()
```

If `RAGAS` doesn't yet exist in `src/zenml/integrations/constants.py`, add it there.

Create `src/zenml/integrations/ragas/evaluators/__init__.py`:

```python
from zenml.integrations.ragas.evaluators.ragas_evaluator import (
    RagasEvaluator,
)
from zenml.integrations.ragas.evaluators.ragas_evaluator_flavor import (
    RagasEvaluatorConfig,
    RagasEvaluatorFlavor,
)

__all__ = [
    "RagasEvaluator",
    "RagasEvaluatorConfig",
    "RagasEvaluatorFlavor",
]
```

Create `src/zenml/integrations/ragas/evaluators/ragas_evaluator_flavor.py`:

```python
"""Config and Flavor for RagasEvaluator."""

from typing import TYPE_CHECKING, Optional, Type

from pydantic import Field

from zenml.evaluators.base_evaluator import (
    BaseEvaluatorConfig,
    BaseEvaluatorFlavor,
)

if TYPE_CHECKING:
    from zenml.integrations.ragas.evaluators.ragas_evaluator import (
        RagasEvaluator,
    )


RAGAS_EVALUATOR_FLAVOR = "ragas"


class RagasEvaluatorConfig(BaseEvaluatorConfig):
    """Config for the Ragas-backed evaluator."""

    judge_model_provider: str = Field(
        "openai",
        description=(
            "LLM provider Ragas uses as judge. Examples: 'openai', "
            "'anthropic'. Defaults to openai"
        ),
    )
    judge_model: str = Field(
        "gpt-4o-mini",
        description=(
            "Specific judge model identifier within the provider. "
            "Example: 'gpt-4o-mini' for openai. Defaults to gpt-4o-mini"
        ),
    )
    embedding_model: Optional[str] = Field(
        None,
        description=(
            "Embedding model used for Ragas similarity metrics. "
            "Example: 'text-embedding-3-small'. Defaults to Ragas's "
            "built-in default for the provider"
        ),
    )


class RagasEvaluatorFlavor(BaseEvaluatorFlavor):
    """Flavor metadata for RagasEvaluator."""

    @property
    def name(self) -> str:
        return RAGAS_EVALUATOR_FLAVOR

    @property
    def config_class(self) -> Type[RagasEvaluatorConfig]:
        return RagasEvaluatorConfig

    @property
    def implementation_class(self) -> Type["RagasEvaluator"]:
        from zenml.integrations.ragas.evaluators.ragas_evaluator import (
            RagasEvaluator,
        )
        return RagasEvaluator
```

Create `src/zenml/integrations/ragas/evaluators/ragas_evaluator.py`:

```python
"""Ragas-backed evaluator: RAG and reference-based eval."""

from zenml.evaluators.base_evaluator import BaseEvaluator
from zenml.evaluators.cases import RAGCase, ReferenceCase
from zenml.evaluators.exceptions import EvaluationModeNotSupportedError
from zenml.evaluators.result import (
    CaseResult,
    EvaluationMode,
    EvaluationResult,
)
from zenml.integrations.ragas.evaluators.ragas_evaluator_flavor import (
    RAGAS_EVALUATOR_FLAVOR,
    RagasEvaluatorConfig,
)


class RagasEvaluator(BaseEvaluator):
    """Evaluator that delegates to the Ragas library.

    Note: Ragas's API surface is young and may shift across versions;
    the exact metric callables in `_run_ragas_*` are pinned via the
    integration's REQUIREMENTS range.
    """

    @property
    def config(self) -> RagasEvaluatorConfig:
        return self._config  # type: ignore[return-value]

    @property
    def supported_modes(self) -> set[EvaluationMode]:
        return {EvaluationMode.RAG, EvaluationMode.REFERENCE}

    def evaluate_rag(
        self,
        cases: list[RAGCase],
        metrics: list[str],
    ) -> EvaluationResult:
        ragas_results = self._run_ragas_rag(cases, metrics)
        cases_out = [
            CaseResult(
                case_id=str(i),
                scores=ragas_results[i],
                passed=True,
                raw={},
            )
            for i in range(len(cases))
        ]
        return EvaluationResult(
            evaluator=RAGAS_EVALUATOR_FLAVOR,
            mode=EvaluationMode.RAG,
            suite_name="",
            cases=cases_out,
            aggregates={},
            metadata={
                "judge_model": self.config.judge_model,
                "metrics": metrics,
            },
        )

    def evaluate_reference(
        self,
        cases: list[ReferenceCase],
        metrics: list[str],
    ) -> EvaluationResult:
        ragas_results = self._run_ragas_reference(cases, metrics)
        cases_out = [
            CaseResult(
                case_id=str(i),
                scores=ragas_results[i],
                passed=True,
                raw={},
            )
            for i in range(len(cases))
        ]
        return EvaluationResult(
            evaluator=RAGAS_EVALUATOR_FLAVOR,
            mode=EvaluationMode.REFERENCE,
            suite_name="",
            cases=cases_out,
            aggregates={},
            metadata={
                "judge_model": self.config.judge_model,
                "metrics": metrics,
            },
        )

    def _run_ragas_rag(
        self,
        cases: list[RAGCase],
        metrics: list[str],
    ) -> list[dict[str, float]]:
        # Lazy-import to avoid pulling Ragas on flavor-registration.
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )

        metric_map = {
            "faithfulness": faithfulness,
            "answer_relevancy": answer_relevancy,
            "context_precision": context_precision,
            "context_recall": context_recall,
        }
        chosen = [metric_map[m] for m in metrics if m in metric_map]
        ds = Dataset.from_dict(
            {
                "question": [c.query for c in cases],
                "contexts": [c.context for c in cases],
                "answer": [c.response for c in cases],
                "ground_truth": [
                    c.expected_answer or "" for c in cases
                ],
            }
        )
        result = evaluate(ds, metrics=chosen)
        # Pseudocode for unwrapping; verify against Ragas's actual return shape:
        return [
            {m: float(result[i][m.name]) for m in chosen}
            for i in range(len(cases))
        ]

    def _run_ragas_reference(
        self,
        cases: list[ReferenceCase],
        metrics: list[str],
    ) -> list[dict[str, float]]:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import answer_correctness, answer_similarity

        metric_map = {
            "answer_correctness": answer_correctness,
            "answer_similarity": answer_similarity,
        }
        chosen = [metric_map[m] for m in metrics if m in metric_map]
        ds = Dataset.from_dict(
            {
                "question": [c.input for c in cases],
                "answer": [c.output for c in cases],
                "ground_truth": [c.expected for c in cases],
            }
        )
        result = evaluate(ds, metrics=chosen)
        return [
            {m: float(result[i][m.name]) for m in chosen}
            for i in range(len(cases))
        ]
```

The `_run_ragas_*` shapes are pseudocode for unwrapping Ragas's result object — verify against the actual API on the pinned version range during implementation.

- [ ] **Step 5: Add `ragas` extras**

Modify `pyproject.toml` — add `ragas` to the `[project.optional-dependencies]` (mirror an existing optional integration):

```toml
ragas = ["ragas>=0.2,<0.4", "datasets"]
```

Verify by checking how `langchain` or `openai` declare extras in the same file.

- [ ] **Step 6: Run tests**

Run: `pytest tests/unit/integrations/ragas/test_ragas_evaluator.py -v`

Expected: 2 passed.

- [ ] **Step 7: Format and commit**

```bash
bash scripts/format.sh
git add src/zenml/integrations/ragas/ src/zenml/integrations/constants.py tests/unit/integrations/ragas/ pyproject.toml
git commit -m "$(cat <<'EOF'
Add ragas integration with RagasEvaluator flavor

New integration package wrapping the Ragas library as an evaluator
flavor. Supports RAG and reference-based eval; pointwise is delegated
to other flavors. Demonstrates that the BaseEvaluator abstraction is
not shaped to a single library.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 14: Documentation

**Files:**
- Create: `docs/book/component-guide/evaluators/evaluators.md`
- Create: `docs/book/component-guide/evaluators/openai.md`
- Create: `docs/book/component-guide/evaluators/ragas.md`
- Create: `docs/book/component-guide/evaluators/custom.md`
- Modify: `docs/book/component-guide/toc.md`

- [ ] **Step 1: Inspect doc style**

Run: `cat /home/demian/Projects/zenml/docs/book/component-guide/experiment-trackers/experiment-trackers.md | head -40`

Mirror the metadata header, tone, and section ordering.

- [ ] **Step 2: Write `evaluators.md` (overview)**

Create `docs/book/component-guide/evaluators/evaluators.md` covering:
- What an evaluator is and why it exists.
- The three modes (pointwise / reference / RAG) with one-paragraph examples each.
- Baseline + gate semantics.
- How to plug in a flavor (`zenml evaluator register ...`).
- Snippet of a pipeline using `evaluate_rag`.

- [ ] **Step 3: Write per-flavor pages**

`docs/book/component-guide/evaluators/openai.md` and `ragas.md` following the existing per-flavor doc pattern: install → register → minimal example → config reference.

- [ ] **Step 4: Write `custom.md`**

How to write a new evaluator flavor: subclass `BaseEvaluator`, declare `supported_modes`, implement the relevant `evaluate_*` methods, add a `Flavor` subclass, register on integration import.

- [ ] **Step 5: Update toc**

Add the new section to `docs/book/component-guide/toc.md` (mirror surrounding entries).

- [ ] **Step 6: Format and commit**

```bash
bash scripts/format.sh
git add docs/book/component-guide/evaluators/ docs/book/component-guide/toc.md
git commit -m "Add docs for the evaluator stack component

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 15: End-to-end smoke test

**Files:**
- Create: `tests/integration/evaluators/test_e2e.py`

This validates the full surface end-to-end: register an evaluator, build a pipeline using `evaluate_rag`, run it with no baseline, run again with a baseline that should not regress, run again with a degraded result that should regress.

- [ ] **Step 1: Build the e2e test**

Use `clean_client` or whatever existing fixture spins up an in-memory ZenML store (find it):

```bash
grep -rn "clean_client\|integration_test_client" /home/demian/Projects/zenml/tests/conftest.py /home/demian/Projects/zenml/tests/integration/ 2>/dev/null | head -5
```

Use a local stub evaluator (subclass `BaseEvaluator` directly inside the test) registered as a one-off flavor via `Client().create_flavor(...)` — the test must not depend on external API keys.

- [ ] **Step 2: Run**

Run: `pytest tests/integration/evaluators/test_e2e.py -v`

Expected: green.

- [ ] **Step 3: Run the full evaluator test surface**

Run: `pytest tests/unit/evaluators/ tests/unit/integrations/openai/test_openai_evaluator.py tests/unit/integrations/ragas/test_ragas_evaluator.py tests/integration/evaluators/ -v`

Expected: all green.

- [ ] **Step 4: Lint sweep**

Run: `bash scripts/format.sh && bash scripts/lint.sh`

Expected: clean (mypy on changed files only is enough — full mypy is too slow).

- [ ] **Step 5: Commit and prepare PR**

```bash
git add tests/integration/evaluators/
git commit -m "Add e2e smoke test for evaluator framework

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

Run `/simplify` per CLAUDE.md before opening the PR. Open the PR against `develop`, label `enhancement` + `release-notes`, and link the design spec.

---

## Self-review (run before handoff)

- [x] Spec coverage:
  - Stack component type → Task 1
  - Module layout → Tasks 2–9
  - BaseEvaluator interface + 3 modes → Task 6
  - Case types → Task 2
  - EvaluationResult + materializer → Tasks 3, 4
  - Baseline resolution (3 strategies) → Tasks 7, 7b
  - Gate semantics (fail/warn/trigger) → Task 9
  - EvalRegression event → Task 8
  - Pre-built steps → Task 9
  - Stack class wiring → Task 10
  - CLI → auto-generated; verified by Task 10's stack tests
  - OpenAIEvaluator flavor → Task 12
  - RagasEvaluator flavor + new integration package → Task 13
  - Migration → Task 11 (conditional)
  - Docs → Task 14
  - E2E validation → Task 15
- [x] Placeholder scan: a couple of spots have `<discovered_test_path>` and `<hash>` placeholders that the engineer fills in from real `grep` / `alembic revision` output — these are concrete instructions to *find* a value, not unspecified work. The Ragas `_run_ragas_*` unwrapping is marked as pseudocode-to-verify, which is honest about Ragas API churn.
- [x] Type consistency: `OnRegression` literal stays `"fail" | "warn" | "trigger"` throughout; `EvaluationMode` enum values match in cases, results, exceptions, and steps; `BaselineSpec` fields match between `baseline.py` definition and `steps.py` defaults; `OpenAIEvaluatorConfig` / `RagasEvaluatorConfig` field names cited only where defined.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-30-llm-evaluator-stack-component.md`. Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session using `executing-plans`, batch execution with checkpoints.

Which approach?
