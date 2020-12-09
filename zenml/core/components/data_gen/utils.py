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

import base64
import enum
import logging
import sys
from abc import ABC
from typing import Dict, List, Text, Any

import apache_beam as beam
import numpy as np
import tensorflow as tf
from dateutil.parser import parse
from google.cloud import bigquery

from zenml.core.components.data_gen import constants
from zenml.core.components.data_gen.constants import DestinationKeys


def is_date(string, fuzzy=False):
    """
    Return whether the string can be interpreted as a date.

    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try:
        parse(tf.compat.as_text(string), fuzzy=fuzzy)
        return True
    except ValueError:
        return False
    except TypeError:
        return False


def is_bytes(data):
    """

    Parameters
    ----------
    data: Bytes-like, checking if it is a string

    Returns: bool, if data is bytes-like
    -------

    """
    return type(data) is bytes


def is_smaller_than(data_dict: Dict[Text, Any], max_size=10485760):
    """

    Parameters
    ----------
    data_dict: Beam data dict to be uploaded into BQ
    max_size: maximum datapoint size in bytes, default 10 MiB

    Returns
    -------
    bool: Whether the data dict is smaller or larger than max_size bytes.

    """
    return sys.getsizeof(data_dict) < max_size


class DataType(enum.IntEnum):
    UNKNOWN = -1
    INT = 0
    FLOAT = 1
    TIMESTAMP = 2
    STRING = 3
    BYTES = 4


BQ_MAPPING = {
    DataType.STRING: 'STRING',
    DataType.INT: 'INTEGER',
    DataType.FLOAT: 'FLOAT',
    DataType.TIMESTAMP: 'TIMESTAMP',
    DataType.BYTES: 'BYTES'
}

_INT64_MIN = np.iinfo(np.int64).min
_INT64_MAX = np.iinfo(np.int64).max


@beam.typehints.with_output_types(beam.typehints.Dict[Text, DataType])
class DtypeInferrer(beam.CombineFn, ABC):
    """A beam.CombineFn to infer data types"""

    @staticmethod
    def _infer_value_type(value) -> DataType:
        try:
            float(value)
        except ValueError:
            # TODO: Check for string here, if not return UNKNOWN
            if is_date(value):
                return DataType.TIMESTAMP
            elif is_bytes(value):
                return DataType.BYTES
            elif isinstance(value, str):
                return DataType.STRING
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

    def extract_output(self, accumulator: Dict[Text, Any], **kwargs) -> \
            Dict[Text, Text]:
        final_schema = {}
        for feature, dtype in accumulator.items():
            if dtype in BQ_MAPPING:
                final_schema[feature] = BQ_MAPPING[dtype]
            else:
                final_schema[feature] = 'STRING'
                logging.error(f'Feature {feature} has UNKNOWN dtype {dtype}')

        return final_schema


def append_tf_example(data: Dict[Text, Any],
                      schema: Dict[Text, Any]) -> tf.train.Example:
    """Add tf example to row"""
    feature = {}
    new_data = data.copy()  # copy of the data

    for key, value in data.items():
        data_type = schema[key]
        kwargs = {}
        if data_type == BQ_MAPPING[DataType.INT]:
            if value is not None:
                kwargs = {'value': [int(value)]}
            feature[key] = tf.train.Feature(
                int64_list=tf.train.Int64List(**kwargs))
        elif data_type == BQ_MAPPING[DataType.FLOAT]:
            if value is not None:
                kwargs = {'value': [float(value)]}
            feature[key] = tf.train.Feature(
                float_list=tf.train.FloatList(**kwargs))
        elif data_type == BQ_MAPPING[DataType.TIMESTAMP]:
            if value is not None:
                ts = parse(tf.compat.as_text(value), fuzzy=True)
                ts = ts.strftime('%Y-%m-%dT%H:%M:%S.%f %Z')
                new_data[key] = ts
                kwargs = {'value': [tf.compat.as_bytes(ts)]}
            feature[key] = tf.train.Feature(
                bytes_list=tf.train.BytesList(**kwargs))
        elif data_type == BQ_MAPPING[DataType.STRING] or \
                data_type == BQ_MAPPING[DataType.BYTES]:
            if value is not None:
                kwargs = {'value': [tf.compat.as_bytes(str(value))]}
            feature[key] = tf.train.Feature(
                bytes_list=tf.train.BytesList(**kwargs))
        else:
            raise RuntimeError(f'Unknown data type {data_type} in the schema '
                               f'for value {value}!')

    tf_example = tf.train.Example(features=tf.train.Features(feature=feature))
    return tf_example


def init_bq_table(project, dataset, table, schema):
    client = bigquery.Client(project=project)

    # check if dataset exists, if not create
    datasets = [d.dataset_id for d in client.list_datasets()]
    if dataset not in datasets:
        dataset = client.create_dataset(dataset)
    else:
        dataset = client.dataset(dataset)

    table_ref = dataset.table(table)
    table = bigquery.Table(table_ref, schema=table_schema(schema))
    client.create_table(table)
    return True


def table_schema(schema):
    # coerce the type of DATA_COL to bytes
    if constants.DATA_COL in schema:
        schema[constants.DATA_COL] = 'BYTES'

    base = [bigquery.SchemaField(k, v) for k, v in schema.items()]
    if constants.DATA_COL not in schema:
        base.append(bigquery.SchemaField(constants.DATA_COL, 'BYTES'))

    return base
