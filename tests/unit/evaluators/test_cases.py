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
