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
"""Typed input case classes for the three evaluation modes."""

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, model_validator


class PointwiseCase(BaseModel):
    """A single (input, output) pair scored against a rubric."""

    input: str
    output: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReferenceCase(BaseModel):
    """A case with a known expected output, scored by similarity."""

    input: str
    output: str
    expected: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RAGCase(BaseModel):
    """A retrieval-augmented case: query, retrieved context, response."""

    query: str
    context: List[str]
    response: str
    expected_answer: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


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
    scale: Tuple[int, int]
    examples: List[RubricExample] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_scale(self) -> "Rubric":
        lo, hi = self.scale
        if lo >= hi:
            raise ValueError(
                f"Rubric scale must have min < max; got ({lo}, {hi})"
            )
        return self
