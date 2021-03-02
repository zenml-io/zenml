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

from typing import Dict, List, Text

import tensorflow_model_analysis as tfma
from google.protobuf.wrappers_pb2 import BoolValue

from zenml.core.steps.evaluator.base_evaluator import BaseEvaluatorStep


def to_camel_case(s):
    return ''.join(list(map(lambda x: x.capitalize(), s.split('_'))))


class AgnosticEvaluator(BaseEvaluatorStep):
    """

    """

    def __init__(self,
                 prediction_key: Text = None,
                 label_key: Text = None,
                 slices: List[List[Text]] = None,
                 metrics: Dict[Text, List[Text]] = None,
                 splits: List[Text] = None):

        super().__init__(prediction_key=prediction_key,
                         label_key=label_key,
                         slices=slices,
                         metrics=metrics,
                         splits=splits)

        self.slices = slices or list()
        self.metrics = metrics or dict()
        self.splits = splits or ['eval']

        self.prediction_key = prediction_key
        self.label_key = label_key

        if prediction_key is None or label_key is None:
            self.infer_prediction_label_pair()

    def build_agnostic_config(self):
        # SLICING SPEC
        slicing_specs = [tfma.SlicingSpec()]
        if self.slices:
            slicing_specs.extend([tfma.SlicingSpec(feature_keys=e)
                                  for e in self.slices])

        # MODEL SPEC
        metric_labels = sorted(list(set(self.metrics.keys())))
        model_specs = [tfma.ModelSpec(label_key=self.label_key,
                                      prediction_key=self.prediction_key)]

        # METRIC SPEC
        baseline = [tfma.MetricConfig(class_name='ExampleCount')]
        metrics_specs = []
        for i, key in enumerate(metric_labels):
            metric_list = baseline.copy()
            metric_list.extend(
                [tfma.MetricConfig(class_name=to_camel_case(m))
                 for m in self.metrics[key]])

            metrics_specs.append(tfma.MetricsSpec(
                # output_names=[key], # TODO: enable multi label
                metrics=metric_list))

        return tfma.EvalConfig(
            model_specs=model_specs,
            slicing_specs=slicing_specs,
            metrics_specs=metrics_specs,
            options=tfma.Options(
                include_default_metrics=BoolValue(value=False)))

    def infer_prediction_label_pair(self):
        raise NotImplementedError('This utility function is not implemented!')
