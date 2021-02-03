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

from typing import Any, List, Tuple, Text, Union, Dict

import six
import tensorflow as tf
from tensorflow_serving.apis import prediction_log_pb2
from tfx.components.bulk_inferrer.prediction_to_example_utils import \
    _parse_predict_log, _parse_classify_log, _parse_multi_inference_log
from tfx.proto import bulk_inferrer_pb2

INPUT_KEY = 'examples'
FEATURE_LIST_TYPE = List[Tuple[Text, List[Union[Text, bytes, float]]]]

# Typehint Any is for compatibility reason.
_OutputExampleSpecType = Union[bulk_inferrer_pb2.OutputExampleSpec, Any]
_PredictOutputType = Union[bulk_inferrer_pb2.PredictOutput, Any]
_ClassifyOutputType = Union[bulk_inferrer_pb2.ClassifyOutput, Any]


def convert_to_dict(prediction_log: prediction_log_pb2.PredictionLog,
                    output_example_spec: _OutputExampleSpecType) \
        -> Dict[Text, Any]:
    """Converts given `prediction_log` to a `tf.train.Example`.

    Args:
      prediction_log: The input prediction log.
      output_example_spec: The spec for how to map prediction results to
      columns in example.

    Returns:
      A `tf.train.Example` converted from the given prediction_log.
    Raises:
      ValueError: If the inference type or signature name in spec does not
      match that in prediction_log.
    """
    specs = output_example_spec.output_columns_spec
    if prediction_log.HasField('multi_inference_log'):
        example, output_features = _parse_multi_inference_log(
            prediction_log.multi_inference_log, output_example_spec)
    else:
        if len(specs) != 1:
            raise ValueError(
                'Got single inference result, so expect single spec in'
                'output_example_spec: %s' % output_example_spec)
        if prediction_log.HasField('regress_log'):
            example = tf.train.Example()
            example.CopyFrom(
                prediction_log.regress_log.request.input.example_list.examples[
                    0])
            output_features = [
                (specs[0].regress_output.value_column,
                 [prediction_log.regress_log.response.result.regressions[
                      0].value])
            ]
        elif prediction_log.HasField('classify_log'):
            example, output_features = _parse_classify_log(
                prediction_log.classify_log, specs[0].classify_output)
        elif prediction_log.HasField('predict_log'):
            example, output_features = _parse_predict_log(
                prediction_log.predict_log,
                specs[0].predict_output)
        else:
            raise ValueError(
                'Unsupported prediction type in prediction_log: %s' %
                prediction_log)
    return to_dict(example, output_features)


def to_dict(example: tf.train.Example,
            features: FEATURE_LIST_TYPE) -> Dict[Text, Any]:
    """Add given features to `example`."""
    output_dict = {}
    possible_types = ["bytes_list", "float_list", "int64_list"]
    feature_map = example.features.feature
    for f, v in feature_map.items():
        for t in possible_types:
            value_list = getattr(v, t, [])
            if len(value_list) >= 1:
                output_dict[f] = value_list
            else:
                output_dict[f] = value_list[0]

    for col, value in features:
        assert col not in output_dict, (
            'column name %s already exists in example: '
            '%s') % (col, example)
        # Note: we only consider two types, bytes and float for now.
        if isinstance(value[0], (six.text_type, six.binary_type)):
            if isinstance(value[0], six.text_type):
                bytes_value = [v.encode('utf-8') for v in value]
            else:
                bytes_value = value
            output_dict[col] = bytes_value
        else:
            output_dict[col] = value

    return output_dict
