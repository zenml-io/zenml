from typing import Any, Dict, List, Text

import attr
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
    input_patterns = attr.ib(type=Dict[Text, Text], default=None)
    output_patterns = attr.ib(type=Dict[Text, Text], default=None)


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

        input_examples = input_dict[constants.EXAMPLES]
        splits = artifact_utils.decode_split_names(
            artifact_utils.get_single_instance(input_examples).split_names)

        input_patterns = dict()
        for split in splits:
            input_patterns.update({
                split: io_utils.all_files_pattern(uri) for uri in
                artifact_utils.get_split_uris(input_examples, split)})

        result.schema_path = schema_path
        result.transform_output = transform_graph_path
        result.input_patterns = input_patterns

        # PARAMETERS ##########################################################
        custom_config = json_utils.loads(
            exec_properties.get(constants.CUSTOM_CONFIG, 'null'))
        result.custom_config = custom_config

        # OUTPUTS #############################################################
        output_artifact = output_dict[constants.TEST_RESULTS]
        output_instance = artifact_utils.get_single_instance(output_artifact)
        output_instance.split_names = artifact_utils.encode_split_names(splits)
        output_patterns = dict()
        for split in splits:
            output_patterns.update({
                split: uri for uri in
                artifact_utils.get_split_uris(output_artifact, split)})

        out_path = artifact_utils.get_single_uri(output_dict[constants.MODEL])
        serving_model_dir = path_utils.serving_model_dir(out_path)

        result.output_patterns = output_patterns
        result.serving_model_dir = serving_model_dir

        return result
