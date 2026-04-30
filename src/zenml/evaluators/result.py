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
"""Output artifact types for the evaluator framework."""

from typing import Any, Dict, List

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
    scores: Dict[str, float]
    passed: bool
    raw: Dict[str, Any] = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    """Output of one evaluator run; emitted as a typed artifact."""

    evaluator: str
    mode: EvaluationMode
    suite_name: str
    cases: List[CaseResult]
    aggregates: Dict[str, float]
    metadata: Dict[str, Any] = Field(default_factory=dict)
