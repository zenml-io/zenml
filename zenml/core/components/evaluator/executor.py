from typing import Any, Dict, List, Text

import apache_beam as beam
import tensorflow_model_analysis as tfma
from absl import logging
from tensorflow_model_analysis import constants as tfma_constants
from tfx import types
from tfx.components.util import tfxio_utils
from tfx.components.util import udf_utils
from tfx.dsl.components.base import base_executor
from tfx.types import artifact_utils
from tfx.utils import io_utils
from tfx.utils import json_utils
from tfx.utils import path_utils
from tfx.utils import proto_utils
from tfx_bsl.tfxio import tensor_adapter

from zenml.core.components.evaluator import constants

_TELEMETRY_DESCRIPTORS = ['Evaluator']


class Executor(base_executor.BaseExecutor):

    def Do(self, input_dict: Dict[Text, List[types.Artifact]],
           output_dict: Dict[Text, List[types.Artifact]],
           exec_properties: Dict[Text, Any]) -> None:

        # Check the inputs
        if constants.EXAMPLES not in input_dict:
            raise ValueError(f'{constants.EXAMPLES} is missing from inputs')
        examples_artifact = input_dict[constants.EXAMPLES]

        # Check the outputs
        if constants.EVALUATION not in output_dict:
            raise ValueError(f'{constants.EVALUATION} is missing from outputs')
        evaluation_artifact = output_dict[constants.EVALUATION]
        output_uri = artifact_utils.get_single_uri(evaluation_artifact)

        # Check the execution parameters
        if constants.EVAL_CONFIG not in exec_properties:
            raise ValueError(f'{constants.EVAL_CONFIG} is missing from exec'
                             f'properties')
        else:
            eval_config = tfma.EvalConfig()
            proto_utils.json_to_proto(exec_properties['eval_config'],
                                      eval_config)
            eval_config = tfma.update_eval_config_with_defaults(eval_config)
            tfma.verify_eval_config(eval_config)

        # Resolve the model
        if constants.MODEL in input_dict:
            model_artifact = input_dict[constants.MODEL]
            model_uri = artifact_utils.get_single_uri(model_artifact)
            model_path = path_utils.serving_model_path(model_uri)

            eval_shared_model_fn = udf_utils.try_get_fn(
                exec_properties=exec_properties,
                fn_name='custom_eval_shared_model') or tfma.default_eval_shared_model

            eval_shared_model = eval_shared_model_fn(
                model_name='',
                eval_saved_model_path=model_path,
                eval_config=eval_config)
        else:
            eval_shared_model = None

        self._log_startup(input_dict, output_dict, exec_properties)

        # Resolve the schema
        schema = None
        if constants.SCHEMA in input_dict:
            schema = io_utils.SchemaReader().read(
                io_utils.get_only_uri_in_dir(
                    artifact_utils.get_single_uri(
                        input_dict[constants.SCHEMA])))

        # Resolve the splits
        splits = exec_properties.get(constants.EXAMPLE_SPLITS, 'null')
        example_splits = json_utils.loads(splits)
        if not example_splits:
            example_splits = ['eval']
            logging.info(f"The {constants.EXAMPLE_SPLITS} parameter is not "
                         f"set, using 'eval' split.")

        # Main pipeline
        logging.info('Evaluating model.')
        with self._make_beam_pipeline() as pipeline:
            examples_list = []
            tensor_adapter_config = None
            if tfma.is_batched_input(eval_shared_model, eval_config):
                tfxio_factory = tfxio_utils.get_tfxio_factory_from_artifact(
                    examples=[
                        artifact_utils.get_single_instance(examples_artifact)],
                    telemetry_descriptors=_TELEMETRY_DESCRIPTORS,
                    schema=schema,
                    raw_record_column_name=tfma_constants.ARROW_INPUT_COLUMN)
                for split in example_splits:
                    file_pattern = io_utils.all_files_pattern(
                        artifact_utils.get_split_uri(examples_artifact,
                                                     split))
                    tfxio = tfxio_factory(file_pattern)
                    data = (pipeline
                            | 'ReadFromTFRecordToArrow[%s]' % split >> tfxio.BeamSource())
                    examples_list.append(data)
                if schema is not None:
                    tensor_adapter_config = tensor_adapter.TensorAdapterConfig(
                        arrow_schema=tfxio.ArrowSchema(),
                        tensor_representations=tfxio.TensorRepresentations())
            else:
                for split in example_splits:
                    file_pattern = io_utils.all_files_pattern(
                        artifact_utils.get_split_uri(examples_artifact,
                                                     split))
                    data = (pipeline
                            | 'ReadFromTFRecord[%s]' % split >>
                            beam.io.ReadFromTFRecord(file_pattern=file_pattern)
                            )
                    examples_list.append(data)

            # Resolve custom extractors
            custom_extractors = udf_utils.try_get_fn(
                exec_properties=exec_properties, fn_name='custom_extractors')
            extractors = None
            if custom_extractors:
                extractors = custom_extractors(
                    eval_shared_model=eval_shared_model,
                    eval_config=eval_config,
                    tensor_adapter_config=tensor_adapter_config)

            # Resolve custom evaluators
            custom_evaluators = udf_utils.try_get_fn(
                exec_properties=exec_properties, fn_name='custom_evaluators')
            evaluators = None
            if custom_evaluators:
                evaluators = custom_evaluators(
                    eval_shared_model=eval_shared_model,
                    eval_config=eval_config,
                    tensor_adapter_config=tensor_adapter_config)

            # Extract, evaluate and write
            (examples_list | 'FlattenExamples' >> beam.Flatten()
             |
             'ExtractEvaluateAndWriteResults' >> tfma.ExtractEvaluateAndWriteResults(
                        eval_config=eval_config,
                        eval_shared_model=eval_shared_model,
                        output_path=output_uri,
                        extractors=extractors,
                        evaluators=evaluators,
                        tensor_adapter_config=tensor_adapter_config))
        logging.info('Evaluation complete. Results written to %s.', output_uri)
