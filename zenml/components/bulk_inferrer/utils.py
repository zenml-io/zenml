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

from typing import Any, Text, Union, Dict

import tensorflow as tf
from tensorflow_serving.apis import prediction_log_pb2
from tfx.components.bulk_inferrer.prediction_to_example_utils import \
    convert
from tfx.proto import bulk_inferrer_pb2

# Typehint Any is for compatibility reason.
_OutputExampleSpecType = Union[bulk_inferrer_pb2.OutputExampleSpec, Any]


def convert_to_dict(prediction_log: prediction_log_pb2.PredictionLog,
                    output_example_spec: _OutputExampleSpecType) \
        -> tf.train.Example:
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
    tf_example = convert(prediction_log=prediction_log,
                         output_example_spec=output_example_spec)
    return tf_example
    # return to_dict(example=tf_example)


def to_dict(example: tf.train.Example) -> Dict[Text, Any]:
    """Add given features to `example`."""
    output_dict = {}
    possible_types = ["bytes_list", "float_list", "int64_list"]
    feature_map = example.features.feature
    for f, v in feature_map.items():
        for t in possible_types:
            # return None if a list is not present in feature
            value_list = getattr(v, t, None)
            # duck typing -> branch is only triggered if a non-empty
            # value list is found
            if value_list:
                data = value_list.value
                if len(data) < 1:
                    output_dict[f] = data
                else:
                    output_dict[f] = data[0]

    return output_dict
