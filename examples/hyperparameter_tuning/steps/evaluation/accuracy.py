import numpy as np
from sklearn import metrics
from steps.evaluation.evaluation_parameters import (
    EvaluationOutputParams,
    EvaluationParams,
)

from zenml.steps.step_decorator import step


@step
def calc_accuracy(
    param: EvaluationParams, y_test: np.ndarray, y_pred: np.ndarray
) -> EvaluationOutputParams.as_output():
    """Calculates the accuracy of the prediction."""
    score = metrics.accuracy_score(y_test, y_pred)
    parameters_print = (
        ""
        if param.model_parameters == {}
        else f" with parameters: {param.model_parameters}"
    )
    print(
        f"{param.evaluation_type}{parameters_print} scored {score*100:.2f}% accuracy"
    )
    return score, "accuracy", param.model_parameters
