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

from typing import Type, Dict, List, Text

import apache_beam as beam
import numpy as np
import pandas as pd
from tensorflow_transform.tf_metadata import schema_utils
from tfx.dsl.components.base import executor_spec
from tfx.types import standard_artifacts
from tfx.types.component_spec import ComponentSpec
from tfx.types.component_spec import ExecutionParameter, ChannelParameter

from zenml.core.components.session_transform import constants as cts
# from zenml.core.components.session_transform import utils
from zenml.core.components.session_transform.component import SessionTransform
from zenml.core.components.session_transform.executor import SessionExecutor
from zenml.core.components.utils import get_function_dict, infer_schema
from zenml.core.components.utils import parse_methods, fill_defaults
from zenml.core.pipelines.config.standard_config import *

METHOD_MAPPING = {PreProcessKeys.RESAMPLING: ResamplingMethods,
                  PreProcessKeys.FILLING: FillingMethods,
                  PreProcessKeys.LABEL_TUNING: LabelTuningMethods}


class SequenceTransformSpec(ComponentSpec):
    """ComponentSpec for the PreTransform"""
    PARAMETERS = {
        cts.TIMESTAMP_COLUMN: ExecutionParameter(type=str),
        cts.CATEGORY_COLUMN: ExecutionParameter(type=str, optional=True),
        cts.FEATURES: ExecutionParameter(type=List[Text]),
        cts.LABELS: ExecutionParameter(type=List[Text]),
        cts.RESAMPLING: ExecutionParameter(type=Dict[Text, List]),
        cts.RESAMPLING + cts.DEFAULT_PREFIX: ExecutionParameter(
            type=Dict[Text, List]),
        cts.FILLING: ExecutionParameter(type=Dict[Text, List]),
        cts.FILLING + cts.DEFAULT_PREFIX: ExecutionParameter(
            type=Dict[Text, List]),
        cts.LABEL_TUNING: ExecutionParameter(type=Dict[Text, List]),
        cts.LABEL_TUNING + cts.DEFAULT_PREFIX: ExecutionParameter(
            type=Dict[Text, List]),
        cts.RESAMPLING_RATE: ExecutionParameter(type=(int, float)),
        cts.TRIP_GAP_THRESHOLD: ExecutionParameter(type=int),
        cts.SEQUENCE_LENGTH: ExecutionParameter(type=int),
        cts.SEQUENCE_SHIFT: ExecutionParameter(type=int),
    }
    INPUTS = {
        'input': ChannelParameter(type=standard_artifacts.Examples),
        'schema': ChannelParameter(type=standard_artifacts.Schema),
    }
    OUTPUTS = {
        'output': ChannelParameter(type=standard_artifacts.Examples)
    }


class SequenceTransformExecutor(SessionExecutor):
    _DEFAULT_FILENAME = 'sequence_transform'

    def get_combiner(self) -> Type[beam.CombineFn]:

        class Combiner(beam.CombineFn):
            def create_accumulator(self, *args, **kwargs):
                return pd.DataFrame()

            def add_input(self, mutable_accumulator, element, *args, **kwargs):
                return mutable_accumulator.append(element)

            def merge_accumulators(self, accumulators, *args, **kwargs):
                return pd.concat(accumulators)

            def extract_output(self, accumulator, *args, **kwargs):
                # Get the required args
                config_dict = args[0]
                s = schema_utils.schema_as_feature_spec(args[1]).feature_spec
                schema = infer_schema(s)

                # Notable columns
                timestamp_column = config_dict[cts.TIMESTAMP_COLUMN]
                category_column = config_dict[cts.CATEGORY_COLUMN]

                # Extract the values from the arrays within the cells
                session = accumulator.applymap(self._array_to_value)

                # Extract the category if there is one
                cat = None
                if category_column:
                    cat = session[category_column].unique()[0].decode('utf-8')

                # Set the timestamp as the index
                session[timestamp_column] = session[timestamp_column].apply(
                    lambda x: pd.to_datetime(x.decode('utf-8')))
                session = session.set_index(timestamp_column)

                # RESAMPLING
                resample_rate = config_dict[cts.RESAMPLING_RATE]
                resample_dict = config_dict[cts.RESAMPLING]
                resample_default_dict = config_dict[
                    cts.RESAMPLING + cts.DEFAULT_PREFIX]

                resample_dict = fill_defaults(resample_dict,
                                              resample_default_dict,
                                              schema)

                resample_function_dict = get_function_dict(resample_dict,
                                                           ResamplingMethods)

                for key, function_list in resample_function_dict.items():
                    assert len(function_list) == 1, \
                        'Please only define a single function for resampling'
                    resample_function_dict[key] = function_list[0]

                feature_list = list(resample_function_dict.keys())
                for feature in feature_list:
                    if feature not in session:
                        session[feature] = None

                resampler = session[feature_list].resample(
                    '{}L'.format(resample_rate))
                session = resampler.agg(resample_function_dict)
                session = session.dropna(
                    subset=config_dict[cts.FEATURES],
                    how='all',
                    axis=0)

                # Resolving the dtype conflicts after resampling
                output_dt_map = self._get_resample_output_dtype(resample_dict,
                                                                schema)
                session = session.astype(output_dt_map)

                # FILLING
                filling_dict = config_dict[cts.FILLING]
                filling_default_dict = config_dict[
                    cts.FILLING + cts.DEFAULT_PREFIX]

                filling_dict = fill_defaults(filling_dict,
                                             filling_default_dict,
                                             schema)

                filling_functions = get_function_dict(filling_dict,
                                                      FillingMethods)

                for key, function_list in filling_functions.items():
                    assert len(function_list) == 1, \
                        'Please only define a single function for filling'
                    filling_functions[key] = function_list[0]

                session = session.agg(filling_functions)

                # Required Keys
                if category_column:
                    session[category_column] = cat

                index_s = session.index.to_series(keep_tz=True)
                session[timestamp_column] = index_s.apply(
                    lambda x: x.strftime("%Y-%m-%d %H:%M:%S.%f %Z"))

                session[timestamp_column + '_epoch'] = \
                    index_s.apply(
                        lambda x: utils.convert_datetime_to_secs(x))

                # LABEL TUNING
                label_dict = config_dict[cts.LABEL_TUNING]
                label_defaults_dict = config_dict[
                    cts.LABEL_TUNING + cts.DEFAULT_PREFIX]

                label_dict = fill_defaults(label_dict,
                                           label_defaults_dict,
                                           schema)

                label_functions = get_function_dict(label_dict,
                                                    LabelTuningMethods)

                label_df = session[list(label_functions.keys())]
                for label, function_list in label_functions.items():
                    for f in function_list:
                        label_df.loc[:, label] = label_df.apply({label: f})

                session.update(label_df)

                session.sort_index(inplace=True)

                subseq_len = config_dict[cts.SEQUENCE_LENGTH]
                shift = config_dict[cts.SEQUENCE_SHIFT]
                return self._extract_sequences(session,
                                               subseq_len,
                                               resample_rate,
                                               shift)

            @staticmethod
            def _array_to_value(value):
                if isinstance(value, np.ndarray) and value.size == 1:
                    return value[0]
                return None

            @staticmethod
            def _get_resample_output_dtype(resampling_config, schema):
                output_dtype_map = {}
                for feature, description in resampling_config.items():
                    method = description[0][MethodKeys.METHOD]
                    params = description[0][MethodKeys.PARAMETERS]

                    output_dtype_map[
                        feature] = methods_resampling.get_output_dtype(
                        input_dtype=schema[feature],
                        method=ResamplingMethods.get_method(method),
                        params=params)

                return output_dtype_map

            @staticmethod
            def _extract_sequences(session, seq_length, window_t, shift):
                sequence_list = []
                for i in range(0, len(session.index), shift):
                    start = session.index[i]
                    end = session.index[i] + pd.to_timedelta(
                        (seq_length - 1) * window_t,
                        unit='ms')
                    ex_sequence = session.loc[start:end, :]

                    if len(ex_sequence.index) == seq_length:
                        sequence_list.append(ex_sequence)
                return sequence_list

        return Combiner


class SequenceTransform(SessionTransform):
    EXECUTOR_SPEC = executor_spec.ExecutorClassSpec(SequenceTransformExecutor)
    SPEC_CLASS = SequenceTransformSpec

    @staticmethod
    def config_parser(config):
        """
        Args:
            config:
        """
        config_dict = {k: None for k, v in
                       SequenceTransformSpec.PARAMETERS.items()
                       if v.optional}

        t_config = config[GlobalKeys.TIMESERIES_]

        # Get the categorization and index columns if they exist
        timestamp_col = t_config[TimeSeriesKeys.PROCESS_SEQUENCE_W_TIMESTAMP]
        config_dict[cts.TIMESTAMP_COLUMN] = timestamp_col
        if TimeSeriesKeys.PROCESS_SEQUENCE_W_CATEGORY_ in t_config:
            cat_col = t_config[TimeSeriesKeys.PROCESS_SEQUENCE_W_CATEGORY_]
            config_dict[cts.CATEGORY_COLUMN] = cat_col

        # Required columns for training
        feat_list = list(config[GlobalKeys.FEATURES].keys())
        label_list = list(config[GlobalKeys.LABELS].keys())

        config_dict[cts.FEATURES] = feat_list
        config_dict[cts.LABELS] = label_list

        # Feature preprocessing dictionaries
        default_config = config[GlobalKeys.PREPROCESSING]

        process_dict = {PreProcessKeys.RESAMPLING: [GlobalKeys.FEATURES,
                                                    GlobalKeys.LABELS],
                        PreProcessKeys.FILLING: [GlobalKeys.FEATURES,
                                                 GlobalKeys.LABELS],
                        PreProcessKeys.LABEL_TUNING: [GlobalKeys.LABELS]}

        for process, keys in process_dict.items():
            # For each sequential preprocessing step, extract defaults first
            config_dict.update({process: {}, process + cts.DEFAULT_PREFIX: {}})
            config_dict[process + cts.DEFAULT_PREFIX].update(parse_methods(
                default_config,
                process,
                METHOD_MAPPING[process]
            ))

            # Then extract any defined methods for that process
            for key in keys:
                assert key not in config_dict[process], \
                    'One feature can only be one of the following ' \
                    'categories: features, evaluator or labels'
                config_dict[process].update(parse_methods(
                    config[key],
                    process,
                    METHOD_MAPPING[process]))

        # Resampling rate
        resample_rate = t_config[TimeSeriesKeys.RESAMPLING_RATE_IN_SECS]
        assert isinstance(resample_rate, (int, float)), \
            '{} must be numerical'.format(
                TimeSeriesKeys.RESAMPLING_RATE_IN_SECS)
        assert resample_rate > 0, \
            '{} must be positive'.format(
                TimeSeriesKeys.RESAMPLING_RATE_IN_SECS)
        config_dict[cts.RESAMPLING_RATE] = resample_rate * 1000

        # Trip threshold
        trip_threshold = t_config[TimeSeriesKeys.TRIP_GAP_THRESHOLD_IN_SECS]
        assert isinstance(trip_threshold, int), '{} must be an integer' \
            .format(TimeSeriesKeys.TRIP_GAP_THRESHOLD_IN_SECS)
        config_dict[cts.TRIP_GAP_THRESHOLD] = trip_threshold

        # Sequence Shift
        seq_shift = t_config[TimeSeriesKeys.SEQUENCE_SHIFT]
        assert isinstance(seq_shift, int), 'sequence_shift must be an integer'
        assert seq_shift > 0, 'sequence_shift must be positive'
        config_dict[cts.SEQUENCE_SHIFT] = seq_shift

        # Sequence Length # TODO: This needs to be in the timeseries block
        seq_len = t_config[TimeSeriesKeys.SEQUENCE_LENGTH]
        assert isinstance(seq_len, int), 'sequence_length must be an integer'
        assert seq_len > 0, 'sequence_length must be positive'
        config_dict[cts.SEQUENCE_LENGTH] = seq_len

        return config_dict
