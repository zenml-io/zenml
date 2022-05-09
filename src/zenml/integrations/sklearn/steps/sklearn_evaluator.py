#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.metrics import classification_report

from zenml.steps.step_interfaces.base_evaluator_step import (
    BaseEvaluatorConfig,
    BaseEvaluatorStep,
)


class SklearnEvaluatorConfig(BaseEvaluatorConfig):
    """Config class for the sklearn evaluator"""

    label_class_column: str


class SklearnEvaluator(BaseEvaluatorStep):
    """A simple step implementation which utilizes sklearn to evaluate the
    performance of a given model on a given test dataset"""

    def entrypoint(  # type: ignore[override]
        self,
        dataset: pd.DataFrame,
        model: BaseEstimator,
        config: SklearnEvaluatorConfig,
    ) -> dict:  # type: ignore[type-arg]
        """Method which is responsible for the computation of the evaluation

        Args:
            dataset: a pandas Dataframe which represents the test dataset
            model: a trained sklearn model
            config: the configuration for the step
        Returns:
            a dictionary which has the evaluation report
        """
        labels = dataset.pop(config.label_class_column)

        predictions = model.predict(dataset)
        predicted_classes = [1 if v > 0.5 else 0 for v in predictions]

        report = classification_report(
            labels, predicted_classes, output_dict=True
        )

        return report  # type: ignore[no-any-return]
