#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
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

from zenml.steps.evaluator.base_evaluator import BaseEvaluatorStep


def to_camel_case(s):
    """
    Converts a given name to camel case and removes any '_'
    """
    return ''.join(list(map(lambda x: x.capitalize(), s.split('_'))))


class TFMAEvaluator(BaseEvaluatorStep):
    """
    TFMA Evaluator step designed for the TF models in ZenML

    It features a specific build_config method which uses the zenml_eval
    signature of the model and produces a flexible tfma.EvalConfig, which can
    work with a wide range of Tensorflow models and TFMA
    """

    CUSTOM_MODULE = 'zenml.steps.evaluator.tfma_module'

    def __init__(self,
                 metrics: Dict[Text, List[Text]],
                 slices: List[List[Text]] = None,
                 output_mapping: Dict[Text, Text] = None,
                 **kwargs):
        """
        Init for the TFMA evaluator

        :param metrics: a dictionary, which specifies a list metrics for each
        label
        :param slices: a list of lists, each element in the inner list include
        a set of features which will be used for slicing on the results
        :param output_mapping: a mapping from label names to output names.
        This is especially useful, when it comes to multi-output models or
        models with unknown output names.
        :param splits: the list of splits to apply the evaluation on
        """

        super(TFMAEvaluator, self).__init__(slices=slices,
                                            metrics=metrics,
                                            output_mapping=output_mapping,
                                            **kwargs)

        self.metrics = metrics
        self.slices = slices or list()

        if output_mapping is None:
            if len(self.metrics.keys()) == 1:
                label = list(self.metrics.keys())[0]
                self.output_mapping = {label: label}
            else:
                raise ValueError('If you are using the evaluator to compute '
                                 'metrics on more than 1 output/label please'
                                 'provide a output_mapping!')
        else:
            self.output_mapping = output_mapping

    def build_config(self, use_defaults=False):
        # SLICING SPEC
        slicing_specs = [tfma.SlicingSpec()]
        if self.slices:
            slicing_specs.extend([tfma.SlicingSpec(feature_keys=e)
                                  for e in self.slices])

        # MODEL SPEC
        metric_labels = sorted(list(set(self.metrics.keys())))
        model_specs = [tfma.ModelSpec(signature_name='zen_eval',
                                      label_keys=self.output_mapping)]

        # METRIC SPEC
        baseline = [tfma.MetricConfig(class_name='ExampleCount')]
        metrics_specs = []
        for i, key in enumerate(metric_labels):
            metrics = baseline.copy()
            metrics.extend([tfma.MetricConfig(class_name=to_camel_case(m))
                            for m in self.metrics[key]])

            metrics_specs.append(tfma.MetricsSpec(
                output_names=[key],
                metrics=metrics))

        return tfma.EvalConfig(
            model_specs=model_specs,
            slicing_specs=slicing_specs,
            metrics_specs=metrics_specs,
            options=tfma.Options(
                include_default_metrics=BoolValue(value=use_defaults)))
