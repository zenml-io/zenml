# Copyright 2019 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""ZenML bulk inferrer executor."""

from tfx_bsl.public.beam import run_inference
from typing import Any, Dict, List, Text

import apache_beam as beam
from absl import logging
from tfx import types
from tfx.dsl.components.base import base_executor
from tfx.proto import bulk_inferrer_pb2
from tfx.types import artifact_utils
from tfx.utils import path_utils
from tfx_bsl.public.proto import model_spec_pb2

from tfx.utils import io_utils
from zenml.core.components.bulk_inferrer.constants import MODEL, EXAMPLES, \
    PREDICTIONS
from zenml.core.components.bulk_inferrer.utils import convert_to_dict
from zenml.core.standards.standard_keys import StepKeys
from zenml.core.steps.inferrer.base_inferrer_step import BaseInferrer
from zenml.utils import source_utils


class BulkInferrerExecutor(base_executor.BaseExecutor):
    """ZenML bulk inferrer executor."""

    def Do(self, input_dict: Dict[Text, List[types.Artifact]],
           output_dict: Dict[Text, List[types.Artifact]],
           exec_properties: Dict[Text, Any]) -> None:

        self._log_startup(input_dict, output_dict, exec_properties)

        source = exec_properties[StepKeys.SOURCE]
        args = exec_properties[StepKeys.ARGS]
        c = source_utils.load_source_path_class(source)
        inferrer_step: BaseInferrer = c(**args)

        output_examples = artifact_utils.get_single_instance(output_dict[PREDICTIONS])

        model = artifact_utils.get_single_instance(input_dict[MODEL])
        model_path = path_utils.serving_model_path(model.uri)
        logging.info('Use exported model from %s.', model_path)

        # output_example_spec = bulk_inferrer_pb2.OutputExampleSpec(
        #     output_columns_spec=[bulk_inferrer_pb2.OutputColumnsSpec(
        #         predict_output=bulk_inferrer_pb2.PredictOutput(
        #             output_columns=[bulk_inferrer_pb2.PredictOutputCol(
        #                 output_key=x,
        #                 output_column=f'{x}_label', ) for x in
        #                 inferrer_step.get_labels()]))])

        model_spec = bulk_inferrer_pb2.ModelSpec()
        saved_model_spec = model_spec_pb2.SavedModelSpec(
            model_path=model_path,
            tag=model_spec.tag,
            signature_name=model_spec.model_signature_name)
        inference_spec = model_spec_pb2.InferenceSpecType()
        inference_spec.saved_model_spec.CopyFrom(saved_model_spec)

        examples = input_dict[EXAMPLES]

        example_uris = {}
        for example_artifact in examples:
            for split in artifact_utils.decode_split_names(
                    example_artifact.split_names):
                example_uris[split] = artifact_utils.get_split_uri(
                    [example_artifact], split)

        output_examples.split_names = artifact_utils.encode_split_names(
            sorted(example_uris.keys()))

        with self._make_beam_pipeline() as pipeline:
            for split, example_uri in example_uris.items():
                output_examples_split_uri = artifact_utils.get_split_uri(
                    [output_examples], split)
                inferrer_step.set_output_uri(output_examples_split_uri)

                _ = (pipeline
                     | 'ReadData[{}]'.format(split) >>
                     beam.io.ReadFromTFRecord(
                         file_pattern=io_utils.all_files_pattern(example_uri))
                     | 'RunInference[{}]'.format(split) >>
                     run_inference.RunInference(inference_spec)
                     | 'ConvertToDict[{}]'.format(split) >>
                     beam.Map(convert_to_dict, output_example_spec)
                     | 'WriteOutput[{}]'.format(split) >>
                     inferrer_step.write_inference_results())

