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

from typing import Any, Dict, List, Text

import apache_beam as beam
from apache_beam.transforms.window import Sessions, GlobalWindows
from tensorflow_data_validation.coders import tf_example_decoder
from tfx import types
from tfx.dsl.components.base.base_executor import BaseExecutor
from tfx.types import artifact_utils
from tfx.types.artifact_utils import get_split_uri
from tfx.utils import io_utils

from zenml.core.components.sequencer import constants
from zenml.core.components.sequencer import utils
from zenml.core.standards.standard_keys import StepKeys


class Executor(BaseExecutor):
    def Do(self,
           input_dict: Dict[Text, List[types.Artifact]],
           output_dict: Dict[Text, List[types.Artifact]],
           exec_properties: Dict[Text, Any]) -> None:
        """

        :param input_dict:
        :param output_dict:
        :param exec_properties:
        :return:
        """

        source = exec_properties[StepKeys.SOURCE]
        args = exec_properties[StepKeys.ARGS]

        # Get split names
        input_artifact = artifact_utils.get_single_instance(
            input_dict[constants.INPUT_EXAMPLES])
        split_names = artifact_utils.decode_split_names(
            input_artifact.split_names)

        # Create output artifact
        output_artifact = artifact_utils.get_single_instance(
            output_dict[constants.OUTPUT_EXAMPLES])
        output_artifact.split_names = artifact_utils.encode_split_names(
            split_names)

        # Get the schema
        schema_path = io_utils.get_only_uri_in_dir(
            artifact_utils.get_single_uri(input_dict[constants.SCHEMA]))
        schema = io_utils.SchemaReader().read(schema_path)

        # TODO: Get the statistics perhaps

        with self._make_beam_pipeline() as p:
            for s in split_names:
                input_uri = io_utils.all_files_pattern(
                    artifact_utils.get_split_uri(input_dict['input'], s))

                # Read and decode the data
                data = \
                    (p
                     | 'Read_' + s >> beam.io.ReadFromTFRecord(
                                file_pattern=input_uri)
                     | 'Decode_' + s >> tf_example_decoder.DecodeTFExample()
                     | 'ToDataFrame_' + s >> beam.ParDo(utils.ToDataframe()))

                # Window into sessions
                s_data = \
                    (data
                     | 'AddCategory_' + s >> beam.ParDo(self.AddKey(),
                                                        category_column)
                     | 'AddTimestamp_' + s >> beam.ParDo(self.AddTimestamp(),
                                                         timestamp_column)
                     | 'Sessions_' + s >> beam.WindowInto(
                                Sessions(trip_gap_threshold))
                     )

                # Combine and transform
                p_data = \
                    (s_data
                     | 'Combine_' + s >> beam.CombinePerKey(
                                self.get_combiner()(),
                                exec_properties,
                                schema)
                     )

                # Write the results
                _ = \
                    (p_data
                     | 'Global_' + s >> beam.WindowInto(GlobalWindows())
                     | 'RemoveKey_' + s >> beam.ParDo(self.RemoveKey())
                     | 'ToExample_' + s >> beam.Map(utils.df_to_example)
                     | 'Serialize_' + s >> beam.Map(utils.serialize)
                     | 'Write_' + s >> beam.io.WriteToTFRecord(
                                get_split_uri([output_artifact], s),
                                file_name_suffix='.gz'))
