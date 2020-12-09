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

import abc
import logging
import os
from typing import Any, Dict, List, Text, Type

import apache_beam as beam
import dateutil
import pytz
from absl import logging
from apache_beam.transforms.window import Sessions, GlobalWindows
from apache_beam.transforms.window import TimestampedValue
from apache_beam.utils.timestamp import Timestamp
from tensorflow_data_validation.coders import tf_example_decoder
from tfx import types
from tfx.components.base import base_executor
from tfx.types import artifact_utils
from tfx.utils import io_utils

from zenml.core.components.session_transform import constants
# from zenml.core.components.session_transform import utils


class SessionExecutor(base_executor.BaseExecutor):
    """Baseline Executor for the SessionTransform component

    It includes a beam pipeline, which windows into sessions with a given gap
    for each split and applies a CombineFn to the sessions.

    In order to use it, follow the instruction given in the component.py
    """
    _DEFAULT_FILENAME = 'session_transform_data'

    def Do(self,
           input_dict: Dict[Text, List[types.Artifact]],
           output_dict: Dict[Text, List[types.Artifact]],
           exec_properties: Dict[Text, Any]) -> None:
        # Start the log
        """
        Args:
            input_dict:
            output_dict:
            exec_properties:
        """
        self._log_startup(input_dict, output_dict, exec_properties)

        # Configuration
        trip_gap_threshold = exec_properties[constants.TRIP_GAP_THRESHOLD]

        # Names of relevant columns
        category_column = exec_properties[constants.CATEGORY_COLUMN]
        timestamp_column = exec_properties[constants.TIMESTAMP_COLUMN]

        # Get each split
        input_artifact = artifact_utils.get_single_instance(
            input_dict['input'])
        split_names = artifact_utils.decode_split_names(
            input_artifact.split_names)

        # Get the schema
        schema_path = io_utils.get_only_uri_in_dir(
            artifact_utils.get_single_uri(input_dict['schema']))
        schema = io_utils.SchemaReader().read(schema_path)

        logging.warning(self._beam_pipeline_args)
        with self._make_beam_pipeline() as p:
            # Iterate Through Each Split
            for split in split_names:
                # Logging
                logging.info('SequenceTransform on the {} split'.format(split))

                input_uri = io_utils.all_files_pattern(
                    artifact_utils.get_split_uri(input_dict['input'], split))

                output_uri = artifact_utils.get_split_uri(
                    output_dict['output'],
                    split)

                output_path = os.path.join(output_uri, self._DEFAULT_FILENAME)

                # Read and decode the data
                data = \
                    (p
                     | 'Read_' + split >> beam.io.ReadFromTFRecord(
                                file_pattern=input_uri)
                     | 'Decode_' + split >>
                     tf_example_decoder.DecodeTFExample()
                     | 'ArrowToDataFrame_' + split >> beam.ParDo(
                                utils.ArrowToDataframe()))

                # Window into sessions
                s_data = \
                    (data
                     | 'AddCategory_' + split >> beam.ParDo(self.AddKey(),
                                                            category_column)
                     | 'AddTimestamp_' + split >> beam.ParDo(
                                self.AddTimestamp(),
                                timestamp_column)
                     | 'Sessions_' + split >> beam.WindowInto(
                                Sessions(trip_gap_threshold))
                     )

                # Combine and transform
                p_data = \
                    (s_data
                     | 'Combine_' + split >> beam.CombinePerKey(
                                self.get_combiner()(),
                                exec_properties,
                                schema)
                     )

                # Write the results
                _ = \
                    (p_data
                     | 'Global_' + split >> beam.WindowInto(GlobalWindows())
                     | 'RemoveKey_' + split >> beam.ParDo(self.RemoveKey())
                     | 'ConvertToExample_' + split >> beam.Map(
                                utils.df_to_example)
                     | 'SerializeDeterministically_' + split >> beam.Map(
                                lambda x: x.SerializeToString(
                                    deterministic=True))
                     | 'WriteSplit_' + split >> beam.io.WriteToTFRecord(
                                output_path, file_name_suffix='.gz'))

    class AddKey(beam.DoFn):
        def process(self, element, category_column):
            """Add the category as a key to the rows

            Args:
                element:
                category_column:
            """
            if category_column:
                element = element.set_index(
                    element[category_column].apply(
                        lambda x: x[0].decode('utf-8')),
                    drop=False)
            else:
                element[constants.DEFAULT_CAT] = constants.DEFAULT_CAT
                element = element.set_index(constants.DEFAULT_CAT)
            return element.iterrows()

    class RemoveKey(beam.DoFn):
        def process(self, element):
            """Remove the key from the output of the CombineFn and return the
            resulting datapoints

            Args:
                element:
            """
            return element[1]

    class AddTimestamp(beam.DoFn):
        @staticmethod
        def extract_t(element, timestamp_column):
            """
            Args:
                element:
                timestamp_column:
            """
            timestamp = dateutil.parser.parse(element[timestamp_column][0])
            timestamp_utc = timestamp.astimezone(pytz.utc)
            return Timestamp.from_utc_datetime(timestamp_utc)

        def process(self, element, timestamp_column):
            """Parse the timestamp and add it to the datapoints

            Args:
                element:
                timestamp_column:
            """
            unix_timestamp = self.extract_t(element[1], timestamp_column)
            yield TimestampedValue(element, unix_timestamp)

    @abc.abstractmethod
    def get_combiner(self) -> Type[beam.CombineFn]:
        """Abstract method which needs to be implemented to with the transform
        logic on the session level
        """
        pass
