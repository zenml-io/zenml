import os
from typing import Dict, Text, List, Any

from tfx import types
from tfx.components.trainer import fn_args_utils
from tfx.components.trainer.executor import GenericExecutor
from tfx.types import artifact_utils

from zenml.core.components.trainer import constants


class ZenMLTrainerExecutor(GenericExecutor):
    def _GetFnArgs(self, input_dict: Dict[Text, List[types.Artifact]],
                   output_dict: Dict[Text, List[types.Artifact]],
                   exec_properties: Dict[Text, Any]) -> fn_args_utils.FnArgs:
        results = super(ZenMLTrainerExecutor, self)._GetFnArgs(input_dict,
                                                               output_dict,
                                                               exec_properties)
        test_results = os.path.join(artifact_utils.get_single_uri(
            output_dict[constants.TEST_RESULTS]), constants.TEST_RESULTS)
        results.test_results = test_results

        return results
