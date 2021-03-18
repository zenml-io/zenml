from typing import Dict, Text, List, Any

from tfx import types
from tfx.components.trainer import fn_args_utils
from tfx.components.trainer.executor import GenericExecutor
from tfx.types import artifact_utils

from zenml.components.trainer import constants


class ZenMLTrainerExecutor(GenericExecutor):
    """
    An adjusted version of the TFX Trainer Generic executor, which also
    handles an additional output artifact while managing the fn_args
    """

    def _GetFnArgs(self, input_dict: Dict[Text, List[types.Artifact]],
                   output_dict: Dict[Text, List[types.Artifact]],
                   exec_properties: Dict[Text, Any]) -> fn_args_utils.FnArgs:
        results = super(ZenMLTrainerExecutor, self)._GetFnArgs(input_dict,
                                                               output_dict,
                                                               exec_properties)
        # TODO[LOW]: fix the fixed eval split
        output_artifact = artifact_utils.get_single_instance(
            output_dict[constants.TEST_RESULTS])
        output_artifact.split_names = artifact_utils.encode_split_names(
            ['eval'])
        test_results = artifact_utils.get_split_uri(
            [output_artifact], 'eval')

        results.test_results = test_results

        return results
