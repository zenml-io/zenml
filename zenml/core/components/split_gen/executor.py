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

import os
from typing import Any, Dict, List, Text

import apache_beam as beam
import tensorflow as tf
from tfx import types
from tfx.components.base.base_executor import BaseExecutor
from tfx.types import artifact_utils
from tfx.types.artifact_utils import get_split_uri
from tfx.utils import io_utils

from zenml.core.components.data_gen.constants import DATA_SPLIT_NAME
from zenml.core.components.split_gen.beam_transforms import WriteSplit
from zenml.core.components.split_gen.utils import parse_schema, \
    parse_statistics
from zenml.core.steps.split.base_split_step import BaseSplitStep
from zenml.utils import source_utils


class Executor(BaseExecutor):
    def Do(self, input_dict: Dict[Text, List[types.Artifact]],
           output_dict: Dict[Text, List[types.Artifact]],
           exec_properties: Dict[Text, Any]) -> None:
        """
        Write description regarding this beautiful executor.

        Args:
            input_dict:
            output_dict:
            exec_properties:
        """
        self._log_startup(input_dict, output_dict, exec_properties)

        schema = parse_schema(input_dict=input_dict)

        statistics = parse_statistics(split_name=DATA_SPLIT_NAME,
                                      statistics=input_dict["statistics"])

        source = exec_properties['source']
        args = exec_properties['args']

        # pass the schema and stats straight to the Step
        args['schema'] = schema
        args['statistics'] = statistics

        c = source_utils.load_source_path_class(source)
        split_step: BaseSplitStep = c(**args)

        # infer the names of the splits from the config
        split_names = split_step.get_split_names()

        # Get output split path
        examples_artifact = artifact_utils.get_single_instance(
            output_dict['examples'])
        examples_artifact.split_names = artifact_utils.encode_split_names(
            split_names)

        split_uris = []
        for artifact in input_dict['input_examples']:
            for split in artifact_utils.decode_split_names(
                    artifact.split_names):
                uri = os.path.join(artifact.uri, split)
                split_uris.append((split, uri))

        with self._make_beam_pipeline() as p:
            # The outer loop will for now only run once
            for split, uri in split_uris:
                input_uri = io_utils.all_files_pattern(uri)

                new_splits = (
                        p
                        | 'ReadData.' + split >> beam.io.ReadFromTFRecord(
                    file_pattern=input_uri)
                        | beam.Map(tf.train.Example.FromString)
                        | 'Split' >> beam.Partition(
                    split_step.partition_fn()[0],
                    split_step.get_num_splits(),
                    **split_step.partition_fn()[1])
                )
                for split_name, new_split in zip(split_names,
                                                 list(new_splits)):
                    # WriteSplit function writes to TFRecord again
                    (new_split
                     | 'Serialize.' + split_name >> beam.Map(
                                lambda x: x.SerializeToString())
                     | 'WriteSplit_' + split_name >> WriteSplit(get_split_uri(
                                output_dict['examples'], split_name)))
