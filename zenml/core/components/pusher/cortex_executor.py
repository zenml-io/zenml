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
"""Cortex pusher executor."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import tempfile
from typing import Any, Dict, List, Text

import cortex
from tfx import types
from tfx.components.pusher import executor as tfx_pusher_executor
from tfx.types import artifact_utils
from tfx.utils import io_utils
from tfx.utils import json_utils
from tfx.utils import path_utils

# Keys for custom_config.
_CUSTOM_CONFIG_KEY = 'custom_config'
SERVING_ARGS_KEY = 'cortex_serving_args'


class Executor(tfx_pusher_executor.Executor):
    """Deploy a model to Cortex serving."""

    def Do(self, input_dict: Dict[Text, List[types.Artifact]],
           output_dict: Dict[Text, List[types.Artifact]],
           exec_properties: Dict[Text, Any]):
        """Overrides the tfx_pusher_executor.

        Args:
          input_dict: Input dict from input key to a list of artifacts,
          including:
            - model_export: exported model from trainer.
            - model_blessing: model blessing path from evaluator.
          output_dict: Output dict from key to a list of artifacts, including:
            - model_push: A list of 'ModelPushPath' artifact of size one. It
            will
              include the model in this push execution if the model was pushed.
          exec_properties: Mostly a passthrough input dict for
            tfx.components.Pusher.executor.custom_config
        Raises:
          ValueError: if custom config not present or not a dict.
          RuntimeError: if
        """
        self._log_startup(input_dict, output_dict, exec_properties)

        # check model blessing
        model_push = artifact_utils.get_single_instance(
            output_dict[tfx_pusher_executor.PUSHED_MODEL_KEY])
        if not self.CheckBlessing(input_dict):
            self._MarkNotPushed(model_push)
            return

        model_export = artifact_utils.get_single_instance(
            input_dict[tfx_pusher_executor.MODEL_KEY])

        custom_config = json_utils.loads(
            exec_properties.get(_CUSTOM_CONFIG_KEY, 'null'))
        if custom_config is not None and not isinstance(custom_config, Dict):
            raise ValueError(
                'custom_config in execution properties needs to be a '
                'dict.')

        cortex_serving_args = custom_config.get(SERVING_ARGS_KEY)
        if not cortex_serving_args:
            raise ValueError(
                '\'cortex_serving_args\' is missing in \'custom_config\'')

        # Deploy the model.
        io_utils.copy_dir(
            src=path_utils.serving_model_path(model_export.uri),
            dst=model_push.uri)
        model_path = model_push.uri

        # Cortex implementation starts here
        # pop the env and initialize client
        cx = cortex.client(cortex_serving_args.pop('env'))

        # load the predictor
        predictor_path = cortex_serving_args.pop('predictor_path')
        with tempfile.TemporaryDirectory() as tmp_dir_name:
            temp_project_dir = tmp_dir_name

            # predictor
            p_dump_path = os.path.join(temp_project_dir, 'predictor.py')
            io_utils.copy_file(predictor_path, p_dump_path)

            # requirements.txt
            reqs = cortex_serving_args.pop('requirements', [])
            if reqs :
                r_dump_path = os.path.join(
                    temp_project_dir, 'requirements.txt')
                io_utils.write_string_file(r_dump_path, '\n'.join(reqs))

            # conda-packages.txt
            c_reqs = cortex_serving_args.pop('conda_packages', [])
            if c_reqs:
                r_dump_path = os.path.join(
                    temp_project_dir, 'conda-packages.txt')
                io_utils.write_string_file(r_dump_path, '\n'.join(c_reqs))

            # edit the api_config
            api_config = cortex_serving_args.pop('api_config')
            if 'config' not in api_config['predictor']:
                api_config['predictor']['config'] = {}
            api_config['predictor']['config']['model_artifact'] = model_path

            # launch the api
            api_config['predictor']['path'] = 'predictor.py'

            # configure the model path
            if 'models' not in api_config['predictor']:
                api_config['predictor']['models'] = {}
            api_config['predictor']['models'].update({'path': model_path})
            cx.create_api(
                api_config,
                project_dir=temp_project_dir,
                **cortex_serving_args)

        self._MarkPushed(
            model_push,
            pushed_destination=model_path)
