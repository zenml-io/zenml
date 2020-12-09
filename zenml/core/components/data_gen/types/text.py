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

import apache_beam as beam

from zenml.core.components.data_gen.types.interface import TypeInterface


class TextConverter(TypeInterface):
    @staticmethod
    def convert(pipeline, output_dict, exec_properties):
        """
        Args:
            pipeline:
            output_dict:
            exec_properties:
        """
        result = (pipeline
                  | beam.Map(lambda x: x)
                  )
        return result
