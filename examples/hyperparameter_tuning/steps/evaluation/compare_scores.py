from dynamic_pipelines.gather_step import GatherStepsParameters
from steps.evaluation.evaluation_parameters import EvaluationOutputParams

from zenml.steps import step


class CompareScoreParams(GatherStepsParameters):
    """Parameters for compare_score step"""

    reduce_min: bool = False
    reduce_max: bool = False


@step
def compare_score(params: CompareScoreParams) -> dict:
    """Compare scores over multiple evaluation outputs."""
    outputs = EvaluationOutputParams.gather(params)

    if params.reduce_min:
        output = min(outputs, key=lambda x: x.score)
        print(
            f"minimal value at {output.model_parameters}. score = {output.score*100:.2f}%"
        )
        return output.model_parameters

    if params.reduce_max:
        output = max(outputs, key=lambda x: x.score)
        print(
            f"maximal value at {output.model_parameters}. score = {output.score*100:.2f}%"
        )
        return output.model_parameters
