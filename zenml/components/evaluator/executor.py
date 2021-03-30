from typing import Any, Dict, List, Text, Callable, Optional

import apache_beam as beam
import tensorflow_model_analysis as tfma
from absl import logging
from tensorflow_model_analysis import constants as tfma_constants
from tfx import types
from tfx.components.util import tfxio_utils
from tfx.dsl.components.base import base_executor
from tfx.types import artifact_utils
from tfx.utils import import_utils
from tfx.utils import io_utils
from tfx.utils import path_utils
from tfx_bsl.tfxio import tensor_adapter

from zenml.components.evaluator import constants
from zenml.logger import get_logger
from zenml.standards.standard_keys import StepKeys
from zenml.steps.evaluator.base_evaluator import BaseEvaluatorStep
from zenml.steps.trainer.utils import TEST_SPLITS
from zenml.utils import path_utils as zenml_path_utils
from zenml.utils import source_utils

logger = get_logger(__name__)


def try_get_fn(module_path: Text,
               fn_name: Text) -> Optional[Callable[..., Any]]:
    try:
        return import_utils.import_func_from_module(module_path, fn_name)
    except (ValueError, AttributeError):
        return None


_TELEMETRY_DESCRIPTORS = ['Evaluator']


class Executor(base_executor.BaseExecutor):

    def Do(self,
           input_dict: Dict[Text, List[types.Artifact]],
           output_dict: Dict[Text, List[types.Artifact]],
           exec_properties: Dict[Text, Any]) -> None:

        # Check the inputs
        if constants.EXAMPLES not in input_dict:
            raise ValueError(f'{constants.EXAMPLES} is missing from inputs')
        examples_artifact = input_dict[constants.EXAMPLES]

        # Create the step with the schema attached if provided
        source = exec_properties[StepKeys.SOURCE]
        args = exec_properties[StepKeys.ARGS]
        c = source_utils.load_source_path_class(source)
        evaluator_step: BaseEvaluatorStep = c(**args)

        splits = evaluator_step.split_mapping[TEST_SPLITS]

        if len(splits) == 0:
            raise AssertionError(
                'In the current configuration of the evaluator step or the '
                'split mapping, there are no splits dedicated for the '
                'evaluation. Either use a "test" split or define a dict '
                'for the split mapping')
        else:
            # Check the outputs
            if constants.EVALUATION not in output_dict:
                raise ValueError(
                    f'{constants.EVALUATION} is missing from outputs')
            evaluation_artifact = output_dict[constants.EVALUATION]
            output_uri = artifact_utils.get_single_uri(evaluation_artifact)

            # Resolve the schema
            schema = None
            if constants.SCHEMA in input_dict:
                schema_artifact = input_dict[constants.SCHEMA]
                schema_uri = artifact_utils.get_single_uri(schema_artifact)
                reader = io_utils.SchemaReader()
                schema = reader.read(io_utils.get_only_uri_in_dir(schema_uri))

            # Check the execution parameters
            eval_config = evaluator_step.build_config()
            eval_config = tfma.update_eval_config_with_defaults(eval_config)
            tfma.verify_eval_config(eval_config)

            # Resolve the model
            if constants.MODEL in input_dict:
                model_artifact = input_dict[constants.MODEL]
                model_uri = artifact_utils.get_single_uri(model_artifact)
                model_path = path_utils.serving_model_path(model_uri)

                model_fn = try_get_fn(evaluator_step.CUSTOM_MODULE,
                                      'custom_eval_shared_model') or tfma.default_eval_shared_model

                eval_shared_model = model_fn(
                    model_name='',  # TODO: Fix with model names
                    eval_saved_model_path=model_path,
                    eval_config=eval_config)
            else:
                eval_shared_model = None

            self._log_startup(input_dict, output_dict, exec_properties)

            # Main pipeline
            logging.info('Evaluating model.')

            with self._make_beam_pipeline() as pipeline:
                examples_list = []
                tensor_adapter_config = None
                if tfma.is_batched_input(eval_shared_model, eval_config):
                    tfxio_factory = tfxio_utils.get_tfxio_factory_from_artifact(
                        examples=[
                            artifact_utils.get_single_instance(
                                examples_artifact)],
                        telemetry_descriptors=_TELEMETRY_DESCRIPTORS,
                        schema=schema,
                        raw_record_column_name=tfma_constants.ARROW_INPUT_COLUMN)

                    for split in splits:
                        split_uri = artifact_utils.get_split_uri(
                            examples_artifact,
                            split)

                        try:
                            if len(zenml_path_utils.list_dir(split_uri)) == 0:
                                raise AssertionError(
                                    f'The saved results found for the split: '
                                    f'{split}. Please make sure that you '
                                    f'run the test_fn in your trainer and '
                                    f'you are working with the right '
                                    f'split_mapping: '
                                    f'{evaluator_step.split_mapping}!')
                        except:
                            # TODO[LOW]: Merge into a single check
                            raise AssertionError(
                                f'The saved results found for the split: '
                                f'{split}. Please make sure that you '
                                f'run the test_fn in your trainer and '
                                f'you are working with the right '
                                f'split_mapping: '
                                f'{evaluator_step.split_mapping}!')

                        file_pattern = io_utils.all_files_pattern(split_uri)
                        tfxio = tfxio_factory(file_pattern)
                        data = (pipeline
                                | 'ReadFromTFRecordToArrow[%s]' % split >> tfxio.BeamSource())
                        examples_list.append(data)
                    if schema is not None:
                        tensor_adapter_config = tensor_adapter.TensorAdapterConfig(
                            arrow_schema=tfxio.ArrowSchema(),
                            tensor_representations=tfxio.TensorRepresentations())
                else:
                    for split in splits:
                        file_pattern = io_utils.all_files_pattern(
                            artifact_utils.get_split_uri(examples_artifact,
                                                         split))
                        data = (pipeline
                                | 'ReadFromTFRecord[%s]' % split >>
                                beam.io.ReadFromTFRecord(
                                    file_pattern=file_pattern)
                                )
                        examples_list.append(data)
                # Resolve custom extractors
                custom_extractors = try_get_fn(evaluator_step.CUSTOM_MODULE,
                                               'custom_extractors')
                extractors = None
                if custom_extractors:
                    extractors = custom_extractors(
                        eval_shared_model=eval_shared_model,
                        eval_config=eval_config,
                        tensor_adapter_config=tensor_adapter_config)

                # Resolve custom evaluators
                custom_evaluators = try_get_fn(evaluator_step.CUSTOM_MODULE,
                                               'custom_evaluators')
                evaluators = None
                if custom_evaluators:
                    evaluators = custom_evaluators(
                        eval_shared_model=eval_shared_model,
                        eval_config=eval_config,
                        tensor_adapter_config=tensor_adapter_config)

                # Extract, evaluate and write
                (examples_list | 'FlattenExamples' >> beam.Flatten()
                 | 'ExtractEvaluateAndWriteResults' >> tfma.ExtractEvaluateAndWriteResults(
                            eval_config=eval_config,
                            eval_shared_model=eval_shared_model,
                            output_path=output_uri,
                            extractors=extractors,
                            evaluators=evaluators,
                            tensor_adapter_config=tensor_adapter_config))
            logging.info('Evaluation complete. Results written to %s.',
                         output_uri)
