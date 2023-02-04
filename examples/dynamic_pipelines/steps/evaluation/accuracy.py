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
        f"{param.evaluation_type}{parameters_print} scored {score*100:.2f}% "
        "accuracy"
    )
    return score, "accuracy", param.model_parameters
