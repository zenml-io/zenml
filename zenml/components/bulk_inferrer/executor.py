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

from typing import Any, Dict, List, Text
from typing import Optional

import apache_beam as beam
from absl import logging
from tfx import types
from tfx.components.util import model_utils
from tfx.dsl.components.base import base_executor
from tfx.proto import bulk_inferrer_pb2
from tfx.types import artifact_utils
from tfx.utils import path_utils
from tfx_bsl.public.proto import model_spec_pb2
from tfx.components.bulk_inferrer.executor import _RunInference

from zenml.components.bulk_inferrer.utils import convert_to_dict
from zenml.components.bulk_inferrer.constants import MODEL, EXAMPLES, \
    MODEL_BLESSING, PREDICTIONS
from zenml.standards.standard_keys import StepKeys
from zenml.steps.inferrer import BaseInferrer
from zenml.utils import source_utils


class BulkInferrerExecutor(base_executor.BaseExecutor):
    """TFX bulk inferrer executor."""

    def Do(self, input_dict: Dict[Text, List[types.Artifact]],
           output_dict: Dict[Text, List[types.Artifact]],
           exec_properties: Dict[Text, Any]) -> None:
        """Runs batch inference on a given model with given input examples.
        Args:
          input_dict: Input dict from input key to a list of Artifacts.
            - examples: examples for inference.
            - model: exported model.
            - model_blessing: model blessing result, optional.
          output_dict: Output dict from output key to a list of Artifacts.
            - output: bulk inference results.
          exec_properties: A dict of execution properties.
            - model_spec: JSON string of bulk_inferrer_pb2.ModelSpec instance.
            - data_spec: JSON string of bulk_inferrer_pb2.DataSpec instance.
        Returns:
          None
        """
        self._log_startup(input_dict, output_dict, exec_properties)

        source = exec_properties[StepKeys.SOURCE]
        args = exec_properties[StepKeys.ARGS]
        c = source_utils.load_source_path_class(source)
        inferrer_step: BaseInferrer = c(**args)

        output_examples = artifact_utils.get_single_instance(
            output_dict[PREDICTIONS])

        if EXAMPLES not in input_dict:
            raise ValueError('\'examples\' is missing in input dict.')
        if MODEL not in input_dict:
            raise ValueError('Input models are not valid, model '
                             'need to be specified.')
        if MODEL_BLESSING in input_dict:
            model_blessing = artifact_utils.get_single_instance(
                input_dict['model_blessing'])
            if not model_utils.is_model_blessed(model_blessing):
                logging.info('Model on %s was not blessed', model_blessing.uri)
                return
        else:
            logging.info(
                'Model blessing is not provided, exported model will be '
                'used.')

        model = artifact_utils.get_single_instance(
            input_dict[MODEL])
        model_path = path_utils.serving_model_path(model.uri)
        logging.info('Use exported model from %s.', model_path)

        output_example_spec = bulk_inferrer_pb2.OutputExampleSpec(
            output_columns_spec=[bulk_inferrer_pb2.OutputColumnsSpec(
                predict_output=bulk_inferrer_pb2.PredictOutput(
                    output_columns=[bulk_inferrer_pb2.PredictOutputCol(
                        output_key=x,
                        output_column=f'{x}_label', ) for x in
                        inferrer_step.get_labels()]))])

        model_spec = bulk_inferrer_pb2.ModelSpec()
        saved_model_spec = model_spec_pb2.SavedModelSpec(
            model_path=model_path,
            tag=model_spec.tag,
            signature_name=model_spec.model_signature_name)
        inference_spec = model_spec_pb2.InferenceSpecType()
        inference_spec.saved_model_spec.CopyFrom(saved_model_spec)

        self._run_model_inference(
            output_example_spec,
            input_dict[EXAMPLES],
            output_examples,
            inference_spec,
            inferrer_step
        )

    def _run_model_inference(
            self,
            output_example_spec: bulk_inferrer_pb2.OutputExampleSpec,
            examples: List[types.Artifact],
            output_examples: Optional[types.Artifact],
            inference_endpoint: model_spec_pb2.InferenceSpecType,
            inferrer_step: BaseInferrer,
    ) -> None:
        """Runs model inference on given examples data.
        Args:
          output_example_spec: bulk_inferrer_pb2.OutputExampleSpec instance.
          examples: List of `standard_artifacts.Examples` artifacts.
          output_examples: Optional output `standard_artifacts.Examples`
          artifact.
          inference_endpoint: Model inference endpoint.
          inferrer_step: Inferrer step supplied in the infer pipeline config.
        """

        # TODO[LOW]: Rewrite this since there is only one split in the
        #  DataGen output
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
                logging.info('Path of output examples split `%s` is %s.',
                             split, output_examples_split_uri)
                _ = (
                    pipeline
                    | 'RunInference[{}]'.format(split) >>
                    _RunInference(example_uri, inference_endpoint)
                    | 'ConvertToDict[{}]'.format(split) >>
                    beam.Map(convert_to_dict, output_example_spec)
                    | 'WriteOutput[{}]'.format(split) >>
                    inferrer_step.write_inference_results())

            logging.info('Output examples written to %s.', output_examples.uri)
