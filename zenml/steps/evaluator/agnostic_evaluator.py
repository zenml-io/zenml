#  Copyright (c) maiot GmbH 2021. All Rights Reserved.
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

from typing import List, Text

import tensorflow_model_analysis as tfma
from google.protobuf.wrappers_pb2 import BoolValue

from zenml.steps.evaluator.base_evaluator import BaseEvaluatorStep


def to_camel_case(s):
    return ''.join(list(map(lambda x: x.capitalize(), s.split('_'))))


class AgnosticEvaluator(BaseEvaluatorStep):
    """

    """

    def __init__(self,
                 label_key: Text,
                 prediction_key: Text = 'output',
                 slices: List[List[Text]] = None,
                 metrics: List[Text] = None,
                 splits: List[Text] = None):

        super().__init__(label_key=label_key,
                         prediction_key=prediction_key,
                         slices=slices,
                         metrics=metrics,
                         splits=splits)

        self.slices = slices or list()
        self.metrics = metrics or list()
        self.splits = splits or ['eval']

        self.prediction_key = prediction_key
        self.label_key = label_key

    def build_config(self):
        # SLICING SPEC
        slicing_specs = [tfma.SlicingSpec()]
        if self.slices:
            slicing_specs.extend([tfma.SlicingSpec(feature_keys=e)
                                  for e in self.slices])

        # MODEL SPEC
        model_specs = [tfma.ModelSpec(label_key=self.label_key,
                                      prediction_key=self.prediction_key)]

        # METRIC SPEC
        baseline = [tfma.MetricConfig(class_name='ExampleCount')]
        for key in self.metrics:
            baseline.append(tfma.MetricConfig(class_name=to_camel_case(key)))

        metrics_specs = [tfma.MetricsSpec(metrics=baseline)]

        return tfma.EvalConfig(
            model_specs=model_specs,
            slicing_specs=slicing_specs,
            metrics_specs=metrics_specs,
            options=tfma.Options(
                include_default_metrics=BoolValue(value=False)))
