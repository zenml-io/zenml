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
"""Utils for data_gen"""

import enum
from abc import ABC
from typing import Dict, List, Text, Any

import apache_beam as beam
import tensorflow as tf

from zenml.logger import get_logger

logger = get_logger(__name__)


class DataType(enum.IntEnum):
    UNKNOWN = -1
    INT = 0
    FLOAT = 1
    BYTES = 2


def _int_converter(value):
    if value is None or value is '' or value is b'':
        return []
    else:
        return [int(value)]


def _float_converter(value):
    if value is None or value is '' or value is b'':
        return []
    else:
        return [float(value)]


def _bytes_converter(value):
    if value is None:
        return []
    else:
        return [tf.compat.as_bytes(value)]


SCHEMA_MAPPING = {
    'INTEGER': DataType.INT,
    'FLOAT': DataType.FLOAT,
    'STRING': DataType.BYTES,
    'BYTES': DataType.BYTES,
    'TIMESTAMP': DataType.BYTES,
    'DATETIME': DataType.BYTES
}

CONVERTER_MAPPING = {
    DataType.UNKNOWN: lambda x: [],
    DataType.INT: _int_converter,
    DataType.FLOAT: _float_converter,
    DataType.BYTES: _bytes_converter,
}


@beam.typehints.with_output_types(beam.typehints.Dict[Text, DataType])
class DtypeInferrer(beam.CombineFn, ABC):
    """A beam.CombineFn to infer data types"""

    @staticmethod
    def _infer_value_type(value) -> DataType:
        try:
            float(value)
        except ValueError:
            if not value:
                return DataType.UNKNOWN

            elif type(value) is bytes or type(value) is str:
                return DataType.BYTES
            else:
                return DataType.UNKNOWN

        except TypeError:
            return DataType.UNKNOWN
        else:
            if float(value).is_integer():
                return DataType.INT
            else:
                return DataType.FLOAT

    def create_accumulator(self, **kwargs) -> Dict[Text, DataType]:
        return {}

    def add_input(self,
                  accumulator: Dict[Text, DataType],
                  element: Dict[Text, bytes],
                  **kwargs,
                  ) -> Dict[Text, DataType]:

        for key, value in element.items():
            previous_type = accumulator.get(key, None)
            current_type = self._infer_value_type(value)

            if previous_type is None or current_type > previous_type:
                accumulator[key] = current_type
        return accumulator

    def merge_accumulators(self,
                           accumulators: List[Dict[Text, DataType]],
                           **kwargs,
                           ) -> Dict[Text, DataType]:

        result = {}
        for single_accumulator in accumulators:
            for feature_name, feature_type in single_accumulator.items():
                if feature_name not in result \
                        or feature_type > result[feature_name]:
                    result[feature_name] = feature_type
        return result

    def extract_output(self,
                       accumulator: Dict[Text, Any],
                       **kwargs) -> Dict[Text, Text]:
        for k in accumulator:
            if k == DataType.UNKNOWN:
                logger.warning(f'Unknown data type in the schema '
                               f'for feature {k}!')
        return accumulator


def append_tf_example(data: Dict[Text, Any],
                      schema: Dict[Text, Any]) -> tf.train.Example:
    """Add tf example to row"""
    feature = {}
    for key, value in data.items():
        data_type = schema[key]
        value = CONVERTER_MAPPING[data_type](value)
        if data_type == DataType.INT:
            feature[key] = tf.train.Feature(
                int64_list=tf.train.Int64List(value=value))
        elif data_type == DataType.FLOAT:
            feature[key] = tf.train.Feature(
                float_list=tf.train.FloatList(value=value))
        elif data_type == DataType.BYTES:
            feature[key] = tf.train.Feature(
                bytes_list=tf.train.BytesList(value=value))
        else:
            feature[key] = tf.train.Feature(
                bytes_list=tf.train.BytesList(value=value))

    tf_example = tf.train.Example(features=tf.train.Features(feature=feature))
    return tf_example
