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

import apache_beam as beam
import os

from zenml.core.steps.data.base_data_step import BaseDataStep

SENTENCE = "sentence"


def read_text(base_path: Text,
              file_ext: Text = ".txt",
              strip_trailing_newlines: bool = True,
              skip_header_lines: int = 0):
    # join with glob character to pick up all files in base directory
    wildcard = "*" + file_ext
    file_pattern = os.path.join(base_path, wildcard)
    return beam.io.ReadFromText(
        file_pattern=file_pattern,
        strip_trailing_newlines=strip_trailing_newlines,
        skip_header_lines=skip_header_lines)


class TextDataStep(BaseDataStep):
    """
    A step that reads in text data from a collection of text files in a
    directory.
    """
    def __init__(self,
                 base_path: Text,
                 schema: Dict = None,
                 file_ext: Text = ".txt",
                 strip_trailing_newlines: bool = True,
                 skip_header_lines: int = 0):
        """
        CSV data step constructor.

        Args:
            base_path: Base path pointing either to the directory containing
             the text files.
            schema: Optional schema providing data type information about the
             data source.
            file_ext: Optional string giving the file extension of text files
             in the base directory.
            strip_trailing_newlines: Boolean indicating whether or not to
             strip newline characters at the end of each line.
            skip_header_lines: Number of lines to skip initially. Must be an
             integer larger or equal 0.
        """
        super().__init__(schema=schema,
                         base_path=base_path,
                         file_ext=file_ext,
                         strip_trailing_newlines=strip_trailing_newlines,
                         skip_header_lines=skip_header_lines)

        self.base_path = base_path
        self.file_ext = file_ext
        self.strip_trailing_newlines = strip_trailing_newlines
        self.skip_header_lines = skip_header_lines

    def read_from_source(self):
        return read_text(base_path=self.base_path,
                         file_ext=self.file_ext,
                         strip_trailing_newlines=self.strip_trailing_newlines,
                         skip_header_lines=self.skip_header_lines)

    def convert_to_dict(self):
        return beam.Map(lambda x: {SENTENCE: x})
