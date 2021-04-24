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
"""CSv Datasource definition"""

import os
from typing import Callable, Text, Dict

import apache_beam as beam
from tfx_bsl.coders import csv_decoder

from zenml.datasources.base_datasource import BaseDatasource
from zenml.logger import get_logger
from zenml.utils import path_utils
from zenml.utils.beam_utils import WriteToTFRecord

logger = get_logger(__name__)


class CSVDatasource(BaseDatasource):
    """ZenML CSV datasource definition.

    Use this for CSV training pipelines.
    """

    def __init__(
            self,
            name: Text,
            path: Text,
            schema: Dict = None,
            **kwargs):
        """
        Create a CSV datasource. Creating this datasource creates a Beam
        pipeline that converts the CSV file into TFRecords for pipelines to
        use.

        The path can be a local path or a Google Cloud Storage bucket
        path for now (S3, Azure coming soon). The path defines the datasource,
        meaning a change in it (including file name) should be dealt with by
        creating another datasource.

        Args:
            name (str): name of datasource.
            path (str): path to csv file.
            schema (str): optional schema for data to conform to.
        """
        self.path = path
        self.schema = schema
        super().__init__(name, path=path, schema=schema, **kwargs)

    def process(self, output_path: Text, make_beam_pipeline: Callable = None):
        wildcard_qualifier = "*"
        file_pattern = os.path.join(self.path, wildcard_qualifier)

        if path_utils.is_dir(self.path):
            csv_files = path_utils.list_dir(self.path)
            if not csv_files:
                raise RuntimeError(
                    'Split pattern {} does not match any files.'.format(
                        file_pattern))
        else:
            if path_utils.file_exists(self.path):
                csv_files = [self.path]
            else:
                raise RuntimeError(f'{self.path} does not exist.')

        # weed out bad file exts with this logic
        allowed_file_exts = [".csv", ".txt"]  # ".dat"
        csv_files = [uri for uri in csv_files if os.path.splitext(uri)[1]
                     in allowed_file_exts]

        logger.info(f'Matched {len(csv_files)}: {csv_files}')

        # Always use header from file
        logger.info(f'Using header from file: {csv_files[0]}.')
        column_names = path_utils.load_csv_header(csv_files[0])
        logger.info(f'Header: {column_names}.')

        with make_beam_pipeline() as p:
            p | 'ReadFromText' >> beam.io.ReadFromText(
                file_pattern=self.path,
                skip_header_lines=1) \
            | 'ParseCSVLine' >> beam.ParDo(csv_decoder.ParseCSVLine(
                delimiter=',')) \
            | 'ExtractParsedCSVLines' >> beam.Map(
                lambda x: dict(zip(column_names, x[0]))) \
            | WriteToTFRecord(self.schema, output_path)
