from enum import Enum

from dynamic_pipelines.gather_step import GatherStepsParameters
from steps.evaluation.evaluation_parameters import EvaluationOutputParams

from zenml.steps import step


class ReduceType(Enum):
    """Simple Enum that indicates which reduction to perform. Either MAX or MIN."""

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
            f"minimal value at {output.model_parameters}. score = {output.score*100:.2f}%"
        )
        return output.model_parameters

    if params.reduce == ReduceType.MAX:
        output = max(outputs, key=lambda x: x.score)
        print(
            f"maximal value at {output.model_parameters}. score = {output.score*100:.2f}%"
        )
        return output.model_parameters
