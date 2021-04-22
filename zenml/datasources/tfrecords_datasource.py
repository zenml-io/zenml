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
"""JSON Datasource definition"""

from pathlib import Path
from typing import Text, Callable, Dict

from zenml.datasources import BaseDatasource
from zenml.utils import path_utils


class TFRecordsDatasource(BaseDatasource):
    """ZenML JSON datasource definition."""

    def __init__(
            self,
            name: Text,
            path: Text,
            schema: Dict = None,
            **kwargs):
        """
        Initialize TFRecords datasource. Data in the TFRecords should be stored
        in TFExamples that represent a list of dicts, where each dict
        represents one datapoint (including label, if required).

        E.g. The data can look like:
            [{
                'age': 20,
                'bmi': 33.3,
                'dbp': 72,
                'has_diabetes': 1,
                'insulin': 0,
                'pedigree': 0.627,
                'pgc': 168,
                'times_pregnant': 1,
                'tst': 35
            }]

        If TFRecords are stored in a different format, please override the
        `process` function of this class and write custom logic to convert
        to a format that looks like the above.

        Args:
            name: Name of datasource.
            path: path to directory of TFRecords files.
            schema (str): optional schema for data to conform to.
        """
        self.path = path
        self.schema = schema
        super().__init__(name, path=path, schema=schema, **kwargs)

    def process(self, output_path: Text, make_beam_pipeline: Callable = None):
        p = Path(self.path).resolve()
        path_utils.copy_dir(str(p), output_path)
