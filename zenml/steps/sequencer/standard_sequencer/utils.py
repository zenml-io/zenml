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


from datetime import datetime

import numpy as np
import pandas as pd
import pytz

from zenml.standards.standard_keys import MethodKeys, DefaultKeys
from zenml.steps.sequencer.standard_sequencer.methods import methods_resampling
from zenml.steps.sequencer.standard_sequencer.methods.standard_methods \
    import ResamplingMethods


def convert_datetime_to_secs(dt):
    delta = dt - datetime(year=1970, month=1, day=1, tzinfo=pytz.utc)
    return int(delta.total_seconds())


def array_to_value(value):
    if isinstance(value, np.ndarray) and value.size == 1:
        return value[0]
    return None


def get_resample_output_dtype(resampling_config, schema):
    output_dtype_map = {}
    for feature, description in resampling_config.items():
        method = description[0][MethodKeys.METHOD]
        params = description[0][MethodKeys.PARAMETERS]

        output_dtype_map[feature] = get_output_dtype(
            input_dtype=schema[feature],
            method=ResamplingMethods.get_method(method),
            params=params)

    return output_dtype_map


def get_output_dtype(input_dtype, method, params):
    if method == methods_resampling.resample_thresholding:
        if type(params['set_value']) is str:
            return str
        else:
            return float
    if input_dtype == 'string':
        if method == methods_resampling.resample_mode:
            return str
    return float


def extract_sequences(session, seq_length, freq, shift):
    sequence_list = []
    for i in range(0, len(session.index), shift):
        start = session.index[i]
        end = session.index[i] + (seq_length - 1) * pd.to_timedelta(freq)
        ex_sequence = session.loc[start:end, :]

        if len(ex_sequence.index) == seq_length:
            sequence_list.append(ex_sequence)
    return sequence_list


def infer_schema(schema):
    """
    Function to infer a schema from input data.
    Args:
        schema: Input dict mapping features to tf.Tensors.

    Returns:
        schema_dict: Dict mapping features to their respective data types.
    """
    schema_dict = dict()
    for feature, descriptions in schema.items():
        dtype = descriptions.dtype
        # These are ugly hacks for hard checking whether its broadly int, float
        #  bool or string.
        if dtype == float or 'float' in str(dtype):
            schema_dict[feature] = DefaultKeys.FLOAT
        elif dtype == int or 'int' in str(dtype):
            schema_dict[feature] = DefaultKeys.INTEGER
        elif dtype == bool or 'bool' in str(dtype):
            schema_dict[feature] = DefaultKeys.BOOLEAN
        elif dtype == str or 'string' in str(dtype):
            schema_dict[feature] = DefaultKeys.STRING
        else:
            raise AssertionError('Cannot infer schema dtype!')
    return schema_dict


def fill_defaults(config, default_config, schema):
    for feature in schema:
        if feature not in config:
            config[feature] = default_config[schema[feature]]
    return config


def get_function_dict(config, methods):
    result = dict()
    for feature, descriptions in config.items():
        result[feature] = []
        for d in descriptions:
            method = d[MethodKeys.METHOD]
            params = d[MethodKeys.PARAMETERS]

            result[feature].append(methods.get_method(method)(**params))

    return result
