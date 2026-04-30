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
