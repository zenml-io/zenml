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
from typing import Dict, Text

import apache_beam as beam
import pandas as pd
import pytz
from apache_beam.transforms.window import Sessions
from apache_beam.transforms.window import TimestampedValue
from apache_beam.utils.timestamp import Timestamp
from tensorflow_transform.tf_metadata import schema_utils

from zenml.steps.sequencer import BaseSequencerStep
from zenml.steps.sequencer.standard_sequencer import utils
from zenml.steps.sequencer.standard_sequencer.methods.standard_methods \
    import ResamplingMethods, FillingMethods
from zenml.utils.preprocessing_utils import parse_methods, DEFAULT_DICT


class StandardSequencer(BaseSequencerStep):

    def __init__(self,
                 timestamp_column: Text,
                 category_column: Text = None,
                 overwrite: Dict[Text, Text] = None,
                 resampling_freq: Text = '1D',
                 gap_threshold: int = 60000,
                 sequence_length: int = 4,
                 sequence_shift: int = 1,
                 **kwargs):
        """
        Initializing the StandardSequencer step, which is responsible for
        extracting sequences from any timeseries dataset.

        The main logic behind this step can be summed up in a few steps
        as follows:

        1. First, we define how to add the corresponding timestamp to
        each datapoint by using the function `get_timestamp_do_fn`. In this
        implementation, the timestamp is expected to be a unix timestamp.

        2. Similarly, we define how to add a categorical key to each
        datapoint if a categorical column is provided.

        3. Following that, we use the timestamp, the categorical key and
        the gap threshold to split the data into so-called 'sessions'

        4. Once the data is split into sessions, we resample the sessions
        based on the `resampling_freq` to create equidistant timestamps,
        fill the missing values and extract the finalized sequences based on
        the `sequence_length` and `sequence_shift`

        :param timestamp_column: string, the name of the column for the
        timestamp resides
        :param category_column: string, the name of the column of a possible
        categorical feature
        :param overwrite: dict, used to overwrite any of the default resampling
        and filling behaviour
        :param resampling_freq: string, the resampling frequency as an
        Offset Alias
        :param gap_threshold: int, the minimum gap between two sessions in
        seconds
        :param sequence_length: int, the desired length of a sequence in terms
        of datapoints
        :param sequence_shift: int, the number steps to shift before extracting
        the next sequence
        :param kwargs: additional params
        """

        self.timestamp_column = timestamp_column
        self.category_column = category_column
        self.overwrite = overwrite
        self.sequence_length = sequence_length
        self.sequence_shift = sequence_shift
        self.resampling_freq = resampling_freq
        self.gap_threshold = gap_threshold

        self.resampling_dict = parse_methods(overwrite or {},
                                             'resampling',
                                             ResamplingMethods)

        self.resampling_default_dict = parse_methods(DEFAULT_DICT,
                                                     'resampling',
                                                     ResamplingMethods)

        self.filling_dict = parse_methods(overwrite or {},
                                          'filling',
                                          FillingMethods)

        self.filling_default_dict = parse_methods(DEFAULT_DICT,
                                                  'filling',
                                                  FillingMethods)

        super(StandardSequencer, self).__init__(
            timestamp_column=timestamp_column,
            category_column=category_column,
            overwrite=overwrite,
            resampling_freq=resampling_freq,
            gap_threshold=gap_threshold,
            sequence_length=sequence_length,
            sequence_shift=sequence_shift,
            **kwargs)

    def get_category_do_fn(self):
        """
        Creates a class which inherits from beam.DoFn to add a categorical key
        to each datapoint

        :return: an instance of the beam.DoFn
        """
        default_category = '__default__'
        category_column = self.category_column

        class AddKey(beam.DoFn):
            def process(self, element):
                """
                Add the category as a key to each element
                """
                if category_column:
                    element = element.set_index(
                        element[category_column].apply(
                            lambda x: x[0].decode('utf-8')),
                        drop=False)
                else:
                    element[default_category] = default_category
                    element = element.set_index(default_category)
                return element.iterrows()

        return AddKey()

    def get_timestamp_do_fn(self):
        """
        Creates a class which inherits from beam.DoFn to add the timestamp
        to each datapoint

        :return: an instance of the beam.DoFn
        """

        timestamp_column = self.timestamp_column

        class AddTimestamp(beam.DoFn):
            def process(self, element):
                """
                Parse the timestamp and add it to the datapoints
                """
                t = element[1][timestamp_column][0]
                timestamp = datetime.fromtimestamp(t, pytz.utc)
                unix_timestamp = Timestamp.from_utc_datetime(timestamp)
                yield TimestampedValue(element, unix_timestamp)

        return AddTimestamp()

    def get_window(self):
        """
        Returns a selected beam windowing strategy

        :return: the selected windowing strategy
        """
        return Sessions(self.gap_threshold)

    def get_combine_fn(self):
        """
        Creates a class which inherits from beam.CombineFn which processes
        sessions and extracts sequences from it

        :return: an instance of the beam.CombineFn
        """
        epoch_suffix = '_epoch'

        timestamp_column = self.timestamp_column
        category_column = self.category_column
        sequence_length = self.sequence_length
        sequence_shift = self.sequence_shift
        resampling_freq = self.resampling_freq
        resampling_dict = self.resampling_dict
        resampling_default_dict = self.resampling_default_dict
        filling_dict = self.filling_dict
        filling_default_dict = self.filling_default_dict

        schema = self.schema

        class SequenceCombine(beam.CombineFn):
            def create_accumulator(self, *args, **kwargs):
                return pd.DataFrame()

            def add_input(self, mutable_accumulator, element, *args, **kwargs):
                return mutable_accumulator.append(element)

            def merge_accumulators(self, accumulators, *args, **kwargs):
                return pd.concat(accumulators)

            def extract_output(self, accumulator, *args, **kwargs):
                # Get the required args
                spec = schema_utils.schema_as_feature_spec(schema).feature_spec
                schema_dict = utils.infer_schema(spec)

                # Extract the values from the arrays within the cells
                session = accumulator.applymap(utils.array_to_value)

                # Extract the category if there is one
                cat = None
                if category_column:
                    cat = session[category_column].unique()[0].decode('utf-8')

                # Set the timestamp as the index
                session[timestamp_column] = session[timestamp_column].apply(
                    lambda x: pd.to_datetime(datetime.fromtimestamp(x,
                                                                    pytz.utc)))
                session = session.set_index(timestamp_column)

                # RESAMPLING
                r_config = utils.fill_defaults(resampling_dict,
                                               resampling_default_dict,
                                               schema_dict)

                resample_functions = utils.get_function_dict(
                    r_config, ResamplingMethods)

                for key, function_list in resample_functions.items():
                    assert len(function_list) == 1, \
                        'Please only define a single function for resampling'
                    resample_functions[key] = function_list[0]

                feature_list = list(resample_functions.keys())
                for feature in feature_list:
                    if feature not in session:
                        session[feature] = None

                resampler = session[feature_list].resample(resampling_freq)
                session = resampler.agg(resample_functions)

                # TODO: Investigate the outcome of disabling this
                # session = session.dropna(subset=config_dict[cts.FEATURES],
                #                          how='all',
                #                          axis=0)

                # Resolving the dtype conflicts after resampling
                output_dt_map = utils.get_resample_output_dtype(
                    resampling_dict,
                    schema_dict)
                session = session.astype(output_dt_map)

                # FILLING
                f_config = utils.fill_defaults(filling_dict,
                                               filling_default_dict,
                                               schema_dict)

                filling_functions = utils.get_function_dict(f_config,
                                                            FillingMethods)

                for key, function_list in filling_functions.items():
                    assert len(function_list) == 1, \
                        'Please only define a single function for filling'
                    filling_functions[key] = function_list[0]
                session = session.agg(filling_functions)

                # Required Keys
                if category_column:
                    session[category_column] = cat

                index_s = session.index.to_series()
                session[timestamp_column] = index_s.apply(
                    lambda x: x.strftime("%Y-%m-%d %H:%M:%S.%f %Z"))

                session[timestamp_column + epoch_suffix] = index_s.apply(
                    lambda x: utils.convert_datetime_to_secs(x))

                session.sort_index(inplace=True)

                return utils.extract_sequences(session,
                                               sequence_length,
                                               resampling_freq,
                                               sequence_shift)

        return SequenceCombine()
