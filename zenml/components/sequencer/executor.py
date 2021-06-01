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
import json
import os
from typing import Any, Dict, List, Text

import apache_beam as beam
from apache_beam.transforms.window import GlobalWindows, TimestampCombiner
from tfx import types
from tfx.components.util import tfxio_utils
from tfx.dsl.components.base.base_executor import BaseExecutor
from tfx.types import artifact_utils
from tfx.utils import io_utils

from zenml.components.sequencer import constants, utils
from zenml.standards.standard_keys import StepKeys
from zenml.steps.sequencer import BaseSequencerStep
from zenml.utils import source_utils

WINDOW_TIMESTAMP = 'window_timestamp'
WINDOW_CATEGORY = 'window_category'


class FinalizeSequence(beam.DoFn):
    def process(self,
                element,
                window=beam.DoFn.WindowParam,
                keep_window_timestamp=False,
                keep_window_category=False):
        """
        Manage the category and timestamp of the output of the CombineFn
        and return the resulting datapoints
        """
        data = element[1][0]

        if keep_window_category:
            if WINDOW_CATEGORY in data.columns:
                raise KeyError(
                    f'If you set the parameter {keep_window_category} to True,'
                    f'make sure that the key "{WINDOW_CATEGORY}" is not used'
                    f'in your datapoint!')
            data[WINDOW_CATEGORY] = element[0]

        if keep_window_timestamp:
            if WINDOW_TIMESTAMP in data.columns:
                raise KeyError(
                    f'If you set the parameter {keep_window_timestamp} to True,'
                    f'make sure that the key "{WINDOW_TIMESTAMP}" is not used'
                    f'in your datapoint!')
            data[WINDOW_TIMESTAMP] = int(window.start)

        return [data]


class Executor(BaseExecutor):
    _DEFAULT_FILENAME = 'sequencer_output'

    def Do(self,
           input_dict: Dict[Text, List[types.Artifact]],
           output_dict: Dict[Text, List[types.Artifact]],
           exec_properties: Dict[Text, Any]) -> None:
        """
        Main execution logic for the Sequencer component

        :param input_dict: input channels
        :param output_dict: output channels
        :param exec_properties: the execution properties defined in the spec
        """

        source = exec_properties[StepKeys.SOURCE]
        args = json.loads(exec_properties[StepKeys.ARGS])

        c = source_utils.load_source_path_class(source)

        # Get the schema
        schema_path = io_utils.get_only_uri_in_dir(
            artifact_utils.get_single_uri(input_dict[constants.SCHEMA]))
        schema = io_utils.SchemaReader().read(schema_path)

        # TODO: Getting the statistics might help the future implementations

        sequence_step: BaseSequencerStep = c(schema=schema,
                                             statistics=None,
                                             **args)

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

        split_and_tfxio = []
        tfxio_factory = tfxio_utils.get_tfxio_factory_from_artifact(
            examples=[input_artifact],
            telemetry_descriptors=['sequencer'])
        for split in split_names:
            uri = artifact_utils.get_split_uri([input_artifact], split)
            split_and_tfxio.append(
                (split, tfxio_factory(io_utils.all_files_pattern(uri))))

        with self._make_beam_pipeline() as p:

            for s, tfxio in split_and_tfxio:
                output_uri = artifact_utils.get_split_uri(
                    output_dict[constants.OUTPUT_EXAMPLES],
                    s)
                output_path = os.path.join(output_uri, self._DEFAULT_FILENAME)

                # Read and decode the data
                data = \
                    (p
                     | 'TFXIORead' + s >> tfxio.BeamSource()
                     | 'ToDataFrame_' + s >> beam.ParDo(
                                utils.ConvertToDataframe()))

                # Window into sessions
                s_data = \
                    (data
                     | 'AddCategory_' + s >> beam.ParDo(
                                sequence_step.get_category_do_fn())
                     | 'AddTimestamp_' + s >> beam.ParDo(
                                sequence_step.get_timestamp_do_fn())
                     | 'Sessions_' + s >> beam.WindowInto(
                                sequence_step.get_window(),
                                timestamp_combiner=TimestampCombiner.OUTPUT_AT_EOW))

                # Combine and transform
                p_data = \
                    (s_data
                     | 'Combine_' + s >> beam.CombinePerKey(
                                sequence_step.get_combine_fn()))

                # Write the results
                _ = \
                    (p_data
                     | 'FinalizeSequence_' + s >> beam.ParDo(
                                FinalizeSequence(),
                                sequence_step.keep_window_timestamp,
                                sequence_step.keep_window_category)
                     | 'Global_' + s >> beam.WindowInto(GlobalWindows())
                     | 'ToExample_' + s >> beam.Map(utils.df_to_example)
                     | 'Serialize_' + s >> beam.Map(utils.serialize)
                     | 'Write_' + s >> beam.io.WriteToTFRecord(
                                output_path,
                                file_name_suffix='.gz'))
