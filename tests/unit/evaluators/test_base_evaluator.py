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
"""Tests for BaseEvaluator, BaseEvaluatorConfig, and BaseEvaluatorFlavor."""

from uuid import UUID

import pytest

from zenml.enums import StackComponentType
from zenml.evaluators.base_evaluator import (
    BaseEvaluator,
    BaseEvaluatorConfig,
    BaseEvaluatorFlavor,
)
from zenml.evaluators.cases import (
    PointwiseCase,
    RAGCase,
    ReferenceCase,
    Rubric,
)
from zenml.evaluators.exceptions import EvaluationModeNotSupportedError
from zenml.evaluators.result import (
    CaseResult,
    EvaluationMode,
    EvaluationResult,
)


class _StubEvaluator(BaseEvaluator):
    """Test double exposing only POINTWISE."""

    @property
    def supported_modes(self):
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
    """Construct a BaseEvaluator subclass for testing.

    StackComponent.__init__ requires id and user as UUID objects (not strings),
    and does not have a project parameter.
    """
    return _StubEvaluator(
        name="stub",
        id=UUID("00000000-0000-0000-0000-000000000001"),
        config=BaseEvaluatorConfig(),
        flavor="stub",
        type=StackComponentType.EVALUATOR,
        user=UUID("00000000-0000-0000-0000-000000000002"),
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


def test_flavor_metadata():
    # BaseEvaluatorFlavor.name is abstract (required by Flavor), so we use a
    # minimal concrete subclass here rather than instantiating the base directly.
    class _TestFlavor(BaseEvaluatorFlavor):
        name = "_test"

        @property
        def implementation_class(self):
            return _StubEvaluator

    f = _TestFlavor()
    assert f.type == StackComponentType.EVALUATOR
