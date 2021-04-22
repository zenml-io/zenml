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

from tfx import types
from tfx.dsl.components.base import base_executor
from tfx.types import artifact_utils

from zenml.components.data_gen.constants import DATA_SPLIT_NAME
from zenml.datasources.base_datasource import BaseDatasource
from zenml.standards.standard_keys import StepKeys
from zenml.utils import source_utils


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
        name = exec_properties[StepKeys.NAME]

        c = source_utils.load_source_path_class(source)
        # TODO [LOW]: Passing _id makes it load
        datasource: BaseDatasource = c(name=name, _id='_id', **args)

        # Get output split path
        examples_artifact = artifact_utils.get_single_instance(
            output_dict[DATA_SPLIT_NAME])
        split_names = [DATA_SPLIT_NAME]
        examples_artifact.split_names = artifact_utils.encode_split_names(
            split_names)
        output_split_path = artifact_utils.get_split_uri(
            [examples_artifact], DATA_SPLIT_NAME)

        datasource.process(
            output_path=output_split_path,
            make_beam_pipeline=self._make_beam_pipeline)
