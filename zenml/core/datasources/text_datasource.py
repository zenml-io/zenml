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

from typing import Text, Dict

from zenml.core.datasources.base_datasource import BaseDatasource
from zenml.core.steps.data.text_data_step import TextDataStep


class TextDatasource(BaseDatasource):
    """Text datasource meant primarily for NLP-based tasks."""

    def __init__(
            self,
            name: Text,
            base_path: Text,
            schema: Dict = None,
            file_ext: Text = ".txt",
            strip_trailing_newlines: bool = True,
            skip_header_lines: int = 0,
            **kwargs):
        """
        Create a CSV datasource. Creating this datasource creates a Beam
        pipeline that converts the CSV file into TFRecords for pipelines to
        use.

        The base_path can be a local path or a Google Cloud Storage bucket
        path for now (S3, Azure coming soon). The path defines the datasource,
        meaning a change in it (including file name) should be dealt with by
        creating another datasource.

        Args:
            name (str): Name of text datasource.
            base_path (str): path to directory containing the text files.
            schema (str): optional schema for data to conform to.
            strip_trailing_newlines (bool): Whether or not to strip the
             newline delimiters at the end of each line.
            skip_header_lines (int): How many header lines to skip in each
             file. Has to be an integer larger than 0.

        """
        super().__init__(name, **kwargs)
        self.base_path = base_path
        self.schema = schema
        self.file_ext = file_ext
        self.strip_trailing_newlines = strip_trailing_newlines
        self.skip_header_lines = skip_header_lines

    def get_data_step(self):
        return TextDataStep(
            base_path=self.base_path,
            schema=self.schema,
            file_ext=self.file_ext,
            strip_trailing_newlines=self.strip_trailing_newlines,
            skip_header_lines=self.skip_header_lines)
