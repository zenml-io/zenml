#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from enum import Enum

from dynamic_pipelines.gather_step import GatherStepsParameters
from steps.evaluation.evaluation_parameters import EvaluationOutputParams

from zenml.steps import step


class ReduceType(Enum):
    """Simple Enum that indicates which reduction to perform."""

    MIN = True
    MAX = False


class CompareScoreParams(GatherStepsParameters):
    """Parameters for compare_score step."""

    reduce: ReduceType


@step
def compare_score(params: CompareScoreParams) -> dict:
    """Compare scores over multiple evaluation outputs."""
    outputs = EvaluationOutputParams.gather(params)

    if params.reduce == ReduceType.MIN:
        output = min(outputs, key=lambda x: x.score)
        print(
            f"minimal value at {output.model_parameters}. score = "
            f"{output.score*100:.2f}%"
        )
        return output.model_parameters

    if params.reduce == ReduceType.MAX:
        output = max(outputs, key=lambda x: x.score)
        print(
            f"maximal value at {output.model_parameters}. score = "
            f"{output.score*100:.2f}%"
        )
        return output.model_parameters
