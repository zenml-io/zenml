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
    """
    Converts a given name to camel case and removes any '_'
    """
    return ''.join(list(map(lambda x: x.capitalize(), s.split('_'))))


class AgnosticEvaluator(BaseEvaluatorStep):
    """
    AgnosticEvaluator step designed to work regardless of the type of the
    trained model

    Through this step, it is possible to use the model_agnostic capabilities of
    TFMA, however this requires the test_results (tf.train.Example) to be saved
    beforehand in a flat format in the trainer step. Once the results are
    saved, you can use the label_key and the prediction_key to specify the
    selected features and compute the desired metrics.

    Note: As of now, it only supports a single label-prediction key pair, we
    are working hard to bring you support for multi-output models as well.
    """

    def __init__(self,
                 label_key: Text,
                 prediction_key: Text,
                 slices: List[List[Text]] = None,
                 metrics: List[Text] = None,
                 **kwargs):
        """
        Init for the AgnosticEvaluator

        :param label_key: string specifying the name of the label in the
        flattened datapoint
        :param prediction_key: string specifying the name of the output in the
        flattened datapoint
        :param slices: a list of lists, each element in the inner list include
        a set of features which will be used for slicing on the results
        :param metrics: list of metrics to be computed
        :param splits: the list of splits to apply the evaluation on
        """
        super(AgnosticEvaluator, self).__init__(label_key=label_key,
                                                prediction_key=prediction_key,
                                                slices=slices,
                                                metrics=metrics,
                                                **kwargs)

        self.slices = slices or list()
        self.metrics = metrics or list()

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
