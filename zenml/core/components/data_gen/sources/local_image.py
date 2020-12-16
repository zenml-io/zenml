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
from apache_beam.io import fileio
from zenml.core.components.data_gen.constants import LocalImageArgs
from zenml.core.components.data_gen.constants import BINARY_DATA, FILE_NAME, \
    BASE_PATH, FILE_PATH, FILE_EXT
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

    wildcard_qualifier = "**"

    # we are ingesting all the files from the base path by
    # supplying the wildcard (hopefully?)
    file_pattern = os.path.join(base_path, wildcard_qualifier)

    files = (pipeline
             | fileio.MatchFiles(file_pattern)
             | fileio.ReadMatches()
             | beam.Reshuffle())

    files_and_contents = (files
                          | beam.Map(read_file_content, base_path)
                          )

    return files_and_contents


def read_file_content(file: beam.io.fileio.ReadableFile,
                      base_path: Text):
    """
    Args:
        file (beam.io.fileio.ReadableFile):
        base_path (Text):
    """
    data_dict = {FILE_PATH: file.metadata.path,
                 BINARY_DATA: file.read(),
                 BASE_PATH: base_path}

    base = os.path.basename(data_dict[FILE_PATH])
    data_dict[FILE_NAME] = base
    data_dict[FILE_EXT] = os.path.splitext(base)[1]

    return data_dict


class LocalImageSource(SourceInterface):
    ARG_KEYS = LocalImageArgs

    def beam_transform(self):
        return ReadFilesFromDisk
