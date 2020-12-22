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
"""Base interface for CSV Data Step"""

import os
from typing import Text, Any, Dict

import apache_beam as beam
from tfx_bsl.coders import csv_decoder

from zenml.core.steps.data.base_data_step import BaseDataStep
from zenml.utils import path_utils
from zenml.utils.logger import get_logger

logger = get_logger(__name__)


@beam.ptransform_fn
@beam.typehints.with_input_types(beam.Pipeline)
@beam.typehints.with_output_types(beam.typehints.Dict[Text, Any])
def read_files_from_disk(pipeline: beam.Pipeline,
                         base_path: Text) -> beam.pvalue.PCollection:
    """
    The Beam PTransform used to read data from a collection of CSV files
    on a local file system.
    Args:
        pipeline: Input beam.Pipeline object coming from a TFX Executor.
        base_path: Base path pointing either to the directory containing the
         CSV files, or to a (single) CSV file.

    Returns:
        A beam.PCollection of data points. Each row in the collection of
         CSV files represents a single data point.

    """
    wildcard_qualifier = "*"
    file_pattern = os.path.join(base_path, wildcard_qualifier)

    if path_utils.is_dir(base_path):
        csv_files = path_utils.list_dir(base_path)
        if not csv_files:
            raise RuntimeError(
                'Split pattern {} does not match any files.'.format(
                    file_pattern))
    else:
        if path_utils.file_exists(base_path):
            csv_files = [base_path]
        else:
            raise RuntimeError(f'{base_path} does not exist.')

    # weed out bad file exts with this logic
    allowed_file_exts = [".csv", ".txt"]  # ".dat"
    csv_files = [uri for uri in csv_files if os.path.splitext(uri)[1]
                 in allowed_file_exts]

    logger.info(f'Matched {len(csv_files)}: {csv_files}')

    # Always use header from file
    logger.info(f'Using header from file: {csv_files[0]}.')
    column_names = path_utils.load_csv_header(csv_files[0])
    logger.info(f'Header: {column_names}.')

    parsed_csv_lines = (
            pipeline
            | 'ReadFromText' >> beam.io.ReadFromText(file_pattern=base_path,
                                                     skip_header_lines=1)
            | 'ParseCSVLine' >> beam.ParDo(csv_decoder.ParseCSVLine(
        delimiter=','))
            | 'ExtractParsedCSVLines' >> beam.Map(
        lambda x: dict(zip(column_names, x[0]))))

    return parsed_csv_lines


class CSVDataStep(BaseDataStep):
    """
    CSV data step to load local tabular data from disk or a remote cloud
    storage bucket.
    """

    def __init__(self, path, schema: Dict = None):
        """
        CSV data step constructor.

        Args:
            path: Base path pointing either to the directory containing the
             CSV files, or to a (single) CSV file.
            schema: Optional schema providing data type information about the
             data source.
        """
        super().__init__(schema=schema, path=path)
        self.path = path

    def read_from_source(self):
        return read_files_from_disk(self.path)
