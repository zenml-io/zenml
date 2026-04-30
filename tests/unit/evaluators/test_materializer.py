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
