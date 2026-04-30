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
from zenml.evaluators.result import (
    CaseResult,
    EvaluationMode,
    EvaluationResult,
)

__all__ = [
    "PointwiseCase",
    "RAGCase",
    "ReferenceCase",
    "Rubric",
    "RubricExample",
    "CaseResult",
    "EvaluationMode",
    "EvaluationResult",
]
