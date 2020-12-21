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
"""Base interface for the Data Step."""

import abc
from typing import Dict
from typing import Text, Any

import apache_beam as beam

from zenml.core.steps.base_step import BaseStep
from zenml.utils.enums import StepTypes


@beam.ptransform_fn
@beam.typehints.with_input_types(beam.Pipeline)
@beam.typehints.with_output_types(beam.typehints.Dict[Text, Any])
def identity_ptransform(pipeline: beam.Pipeline):
    return pipeline


class BaseDataStep(BaseStep):
    """
    Base class for all data steps. These steps are used to specify a data
    source that is read from in a data or a training pipeline.
    """

    STEP_TYPE = StepTypes.data.name

    def __init__(self, schema: Dict = None, **kwargs):
        """
        Base data step constructor. Custom data sources can be implemented
        by defining classes that inherit from this class. Any custom data
        source must implement the `read_from_source` method.

        Args:
            schema: Optional schema of the data, a dict mapping feature names
             in the data to their respective data types.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(schema=schema, **kwargs)
        self.schema = schema

    @abc.abstractmethod
    def read_from_source(self):
        pass

    def convert_to_dict(self):
        return identity_ptransform()
