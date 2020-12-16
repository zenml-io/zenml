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
from typing import Text, Dict, Any

import apache_beam as beam
from tfx.utils import io_utils
from tfx_bsl.coders import csv_decoder

from zenml.core.components.data_gen.constants import LocalCSVArgs
from zenml.core.components.data_gen.sources.interface import SourceInterface


@beam.ptransform_fn
@beam.typehints.with_input_types(beam.Pipeline)
@beam.typehints.with_output_types(beam.typehints.Dict[Text, Any])
def ReadFilesFromDisk(pipeline: beam.Pipeline,
                      source_args: Dict[Text, Any]) -> beam.pvalue.PCollection:
    """
    Args:
        pipeline (beam.Pipeline):
        source_args:
    """
    base_path = source_args['base_path']

    wildcard_qualifier = "*"

    # we are ingesting all the files from the base path by
    # supplying the wildcard (hopefully?)
    file_pattern = os.path.join(base_path, wildcard_qualifier)

    import tensorflow as tf
    csv_files = tf.io.gfile.glob(file_pattern)
    if not csv_files:
        raise RuntimeError(
            'Split pattern {} does not match any files.'.format(file_pattern))

    column_names = io_utils.load_csv_column_names(csv_files[0])

    parsed_csv_lines = (
            pipeline
            | 'ReadFromText' >> beam.io.ReadFromText(file_pattern=file_pattern,
                                                     skip_header_lines=1)
            | 'ParseCSVLine' >> beam.ParDo(csv_decoder.ParseCSVLine(
        delimiter=','))
            | 'ExtractParsedCSVLines' >> beam.Map(lambda x:
                                                  dict(zip(column_names, x))))

    return parsed_csv_lines


class LocalCSVSource(SourceInterface):
    ARG_KEYS = LocalCSVArgs

    def beam_transform(self):
        return ReadFilesFromDisk
