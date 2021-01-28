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

from zenml.core.steps.evaluator.base_evaluator import BaseEvaluatorStep
from zenml.utils.enums import StepTypes


def to_camel_case(s):
    """
    Args:
        s:
    """
    return ''.join(list(map(lambda x: x.capitalize(), s.split('_'))))


class TFMAEvaluator(BaseEvaluatorStep):
    """
    Custom TFMA Evaluator step. This step does not get its own derived class,
    it derives directly from the BaseStep class.
    """
    def __init__(self,
                 slices: List[List[Text]] = None,
                 metrics: Dict[Text, List[Text]] = None):
        super().__init__(slices=slices, metrics=metrics)
        self.slices = slices or list()
        self.metrics = metrics or dict()

    def build_eval_config(self, use_defaults=False):

        # SLICING SPEC
        slicing_specs = [tfma.SlicingSpec()]

        if self.slices:
            slicing_specs.extend([tfma.SlicingSpec(feature_keys=e)
                                  for e in self.slices])

        # MODEL SPEC
        metric_labels = sorted(list(set(self.metrics.keys())))

        model_specs = [tfma.ModelSpec(
            signature_name='zen_eval',
            label_keys={l: 'label_{}_xf'.format(l)
                        for i, l in enumerate(metric_labels)})]

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
