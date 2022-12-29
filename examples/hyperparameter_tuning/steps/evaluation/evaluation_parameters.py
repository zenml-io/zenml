from dynamic_pipelines.gather_step import OutputParameters

from zenml.steps.base_parameters import BaseParameters


class EvaluationOutputParams(OutputParameters):
    """Output parameters of evaluation steps"""

    score: float
    metric_name: str
    model_parameters: dict


class EvaluationParams(BaseParameters):
    """Parameters for evaluation steps"""

    evaluation_type: str
    model_parameters: dict = {}
