import json
from typing import Any, Dict, List, Text

import attr
from tensorflow.python.lib.io import file_io
from tfx import types
from tfx.components.trainer import fn_args_utils
from tfx.components.trainer.executor import GenericExecutor
from tfx.components.trainer.fn_args_utils import FnArgs
from tfx.types import artifact_utils
from tfx.utils import io_utils
from tfx.utils import json_utils
from tfx.utils import path_utils

from zenml.components.trainer import constants
from zenml.logger import get_logger

logger = get_logger(__name__)

_TELEMETRY_DESCRIPTORS = ['Trainer']


class ZenMLTrainerArgs(FnArgs):
    train_files = attr.ib(type=Dict[Text, List[Text]])
    eval_files = attr.ib(type=Dict[Text, List[Text]])
    test_files = attr.ib(type=Dict[Text, List[Text]])

    test_results = attr.ib(type=Text, default=None)


class ZenMLTrainerExecutor(GenericExecutor):
    """
    An adjusted version of the TFX Trainer Generic executor, which also
    handles an additional output artifact while managing the fn_args
    """

    def _GetFnArgs(self,
                   input_dict: Dict[Text, List[types.Artifact]],
                   output_dict: Dict[Text, List[types.Artifact]],
                   exec_properties: Dict[Text, Any]) -> fn_args_utils.FnArgs:

        result = ZenMLTrainerArgs()

        # INPUTS ##############################################################
        if input_dict.get(constants.BASE_MODEL):
            base_model = path_utils.serving_model_path(
                artifact_utils.get_single_uri(
                    input_dict[constants.BASE_MODEL]))
        else:
            base_model = None

        if input_dict.get(constants.HYPERPARAMETERS):
            hyperparameters_file = io_utils.get_only_uri_in_dir(
                artifact_utils.get_single_uri(
                    input_dict[constants.HYPERPARAMETERS]))
            hyperparameters_config = json.loads(
                file_io.read_file_to_string(hyperparameters_file))
        else:
            hyperparameters_config = None

        if input_dict.get(constants.TRANSFORM_GRAPH):
            transform_graph_path = artifact_utils.get_single_uri(
                input_dict[constants.TRANSFORM_GRAPH])
        else:
            transform_graph_path = None

        if input_dict.get(constants.SCHEMA):
            schema_path = io_utils.get_only_uri_in_dir(
                artifact_utils.get_single_uri(
                    input_dict[constants.SCHEMA]))
        else:
            schema_path = None

        result.base_model = base_model
        result.hyperparameters = hyperparameters_config
        result.schema_path = schema_path
        result.transform_graph_path = transform_graph_path
        result.transform_output = result.transform_graph_path

        # PARAMETERS ##########################################################

        # Load and deserialize custom config from execution properties.
        # Note that in the component interface the default serialization of custom
        # config is 'null' instead of '{}'. Therefore we need to default the
        # json_utils.loads to 'null' then populate it with an empty dict when
        # needed.
        custom_config = json_utils.loads(
            exec_properties.get(constants.CUSTOM_CONFIG, 'null'))

        # Examples artifact
        input_examples = input_dict[constants.EXAMPLES]
        splits = artifact_utils.decode_split_names(
            artifact_utils.get_single_instance(input_examples).split_names)

        # Train files
        if constants.TRAIN_SPLITS in custom_config:
            train_splits = custom_config[constants.TRAIN_SPLITS]
        else:
            train_splits = ['train']
            logger.info(f'There are no splits specified for the training, '
                        f'{train_splits} as the default value.')

        train_files = dict()
        for split in train_splits:
            assert split in splits, f'There is no such split as: {split}'
            train_files.update(
                {split: io_utils.all_files_pattern(uri) for uri in
                 artifact_utils.get_split_uris(input_examples, split)})

        # Eval files
        if constants.EVAL_SPLITS in custom_config:
            eval_splits = custom_config[constants.EVAL_SPLITS]
        else:
            eval_splits = ['eval']
            logger.info(f'There are no splits specified for the evaluation, '
                        f'{eval_splits} as the default value.')

        eval_files = dict()
        for split in eval_splits:
            assert split in splits, f'There is no such split as: {split}'
            eval_files.update(
                {split: io_utils.all_files_pattern(uri) for uri in
                 artifact_utils.get_split_uris(input_examples, split)})

        # Test files
        if constants.TEST_SPLITS in custom_config:
            test_splits = custom_config[constants.TEST_SPLITS]
        else:
            if 'test' in splits:
                test_splits = ['test']
                logger.info(f'There are no splits specified for the test, but '
                            f'a "test" split is detected, using {test_splits} '
                            f'as the default value.')

            else:
                test_splits = []
                logger.info(f'There are no splits specified for the test and '
                            f'there are no detected splits, using '
                            f'{test_splits} as the default value.')

        test_files = dict()
        for split in test_splits:
            assert split in splits, f'There is no such split as: {split}'
            test_files.update(
                {split: io_utils.all_files_pattern(uri) for uri in
                 artifact_utils.get_split_uris(input_examples, split)})

        result.custom_config = custom_config
        result.train_files = train_files
        result.eval_files = eval_files
        result.test_files = test_files

        # OUTPUTS #############################################################

        output_artifact = artifact_utils.get_single_instance(
            output_dict[constants.TEST_RESULTS])
        output_artifact.split_names = artifact_utils.encode_split_names(
            test_splits)

        result_files = {
            split: artifact_utils.get_split_uri([output_artifact], split)
            for split in test_splits
        }

        output_path = artifact_utils.get_single_uri(
            output_dict[constants.MODEL])
        serving_model_dir = path_utils.serving_model_dir(output_path)
        eval_model_dir = path_utils.eval_model_dir(output_path)
        model_run_dir = artifact_utils.get_single_uri(
            output_dict[constants.MODEL_RUN])

        result.test_results = result_files
        result.serving_model_dir = serving_model_dir
        result.eval_model_dir = eval_model_dir
        result.model_run_dir = model_run_dir

        return result
