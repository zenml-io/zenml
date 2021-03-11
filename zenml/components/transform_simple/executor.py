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

from typing import Dict, Text, Any, List

import apache_beam as beam
from tfx import types
from tfx.components.example_gen.base_example_gen_executor import _WriteSplit
from tfx.dsl.components.base import base_executor
from tfx.types import artifact_utils

from zenml.components.data_gen import utils
from zenml.components.data_gen.constants import DATA_SPLIT_NAME
from zenml.standards.standard_keys import StepKeys
from zenml.steps.data.base_data_step import BaseDataStep
from zenml.utils import source_utils


@beam.ptransform_fn
@beam.typehints.with_input_types(beam.typehints.Dict[Text, Any])
@beam.typehints.with_output_types(beam.pvalue.PDone)
def WriteToTFRecord(datapoints: Dict[Text, Any],
                    schema: Dict[Text, Any],
                    output_split_path: Text) -> beam.pvalue.PDone:
    """Infers schema and writes to TFRecord"""
    # Obtain the schema
    if schema:
        schema_dict = {k: utils.SCHEMA_MAPPING[v] for k, v in schema.items()}
    else:
        schema = (datapoints
                  | 'Schema' >> beam.CombineGlobally(utils.DtypeInferrer()))
        schema_dict = beam.pvalue.AsSingleton(schema)

    return (datapoints
            | 'ToTFExample' >> beam.Map(utils.append_tf_example, schema_dict)
            | 'WriteToTFRecord' >> _WriteSplit(
                output_split_path=output_split_path
            ))


class DataExecutor(base_executor.BaseExecutor):

    def Do(self,
           input_dict: Dict[Text, List[types.Artifact]],
           output_dict: Dict[Text, List[types.Artifact]],
           exec_properties: Dict[Text, Any]) -> None:
        """
        Args:
            input_dict:
            output_dict:
            exec_properties:
        """
        source = exec_properties[StepKeys.SOURCE]
        args = exec_properties[StepKeys.ARGS]

        c = source_utils.load_source_path_class(source)
        data_step: BaseDataStep = c(**args)

        # Get output split path
        examples_artifact = artifact_utils.get_single_instance(
            output_dict[DATA_SPLIT_NAME])
        split_names = [DATA_SPLIT_NAME]
        examples_artifact.split_names = artifact_utils.encode_split_names(
            split_names)
        output_split_path = artifact_utils.get_split_uri(
            [examples_artifact], DATA_SPLIT_NAME)

        with self._make_beam_pipeline() as p:
            (p
             | data_step.read_from_source()
             # | data_step.convert_to_dict()
             | WriteToTFRecord(data_step.schema, output_split_path))
