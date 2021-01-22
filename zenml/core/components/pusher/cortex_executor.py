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

import time
from typing import Any, Dict, List, Text

from googleapiclient import discovery
from tfx import types
from tfx.components.pusher import executor as tfx_pusher_executor
from tfx.extensions.google_cloud_ai_platform import runner
from tfx.proto import pusher_pb2
from tfx.types import artifact_utils
from tfx.utils import io_utils
from tfx.utils import json_utils
from tfx.utils import path_utils
from tfx.utils import telemetry_utils

# Google Cloud AI Platform's ModelVersion resource path format.
# https://cloud.google.com/ai-platform/prediction/docs/reference/rest/v1
# /projects.models.versions/get
_CAIP_MODEL_VERSION_PATH_FORMAT = (
    'projects/{project_id}/models/{model}/versions/{version}')

# Keys to the items in custom_config passed as a part of exec_properties.
SERVING_ARGS_KEY = 'ai_platform_serving_args'
# Keys for custom_config.
_CUSTOM_CONFIG_KEY = 'custom_config'

# Aliasing of enum for better readability.
_Versioning = pusher_pb2.Versioning

# Key for model in executor input_dict.
MODEL_KEY = 'model'
# Key for model blessing in executor input_dict.
MODEL_BLESSING_KEY = 'model_blessing'
# Key for infra blessing in executor input_dict.
INFRA_BLESSING_KEY = 'infra_blessing'
# Key for pushed model in executor output_dict.
PUSHED_MODEL_KEY = 'pushed_model'

# Key for PushedModel artifact properties.
_PUSHED_KEY = 'pushed'
_PUSHED_DESTINATION_KEY = 'pushed_destination'
_PUSHED_VERSION_KEY = 'pushed_version'


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
            tfx.components.Pusher.executor.
            custom_config.ai_platform_serving_args
            is consumed by this class.  For the full set of parameters
            supported by
            Google Cloud AI Platform, refer to
            https://cloud.google.com/ml-engine/docs/tensorflow/deploying
            -models#creating_a_model_version.

        Raises:
          ValueError:
            If ai_platform_serving_args is not in
            exec_properties.custom_config.
            If Serving model path does not start with gs://.
          RuntimeError: if the Google Cloud AI Platform training job failed.
        """
        self._log_startup(input_dict, output_dict, exec_properties)
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

        ai_platform_serving_args = custom_config.get(SERVING_ARGS_KEY)
        if not ai_platform_serving_args:
            raise ValueError(
                '\'ai_platform_serving_args\' is missing in \'custom_config\'')
        service_name, api_version = runner.get_service_name_and_api_version(
            ai_platform_serving_args)
        # Deploy the model.
        io_utils.copy_dir(
            src=path_utils.serving_model_path(model_export.uri),
            dst=model_push.uri)
        model_path = model_push.uri
        # TODO(jjong): Introduce Versioning.
        # Note that we're adding "v" prefix as Cloud AI Prediction only
        # allows the
        # version name that starts with letters, and contains letters, digits,
        # underscore only.
        model_version = 'v{}'.format(int(time.time()))
        executor_class_path = '%s.%s' % (self.__class__.__module__,
                                         self.__class__.__name__)
        with telemetry_utils.scoped_labels(
                {telemetry_utils.LABEL_TFX_EXECUTOR: executor_class_path}):
            job_labels = telemetry_utils.get_labels_dict()
        runner.deploy_model_for_aip_prediction(
            discovery.build(service_name, api_version),
            model_path,
            model_version,
            ai_platform_serving_args,
            job_labels,
        )

        self._MarkPushed(
            model_push,
            pushed_destination=_CAIP_MODEL_VERSION_PATH_FORMAT.format(
                project_id=ai_platform_serving_args['project_id'],
                model=ai_platform_serving_args['model_name'],
                version=model_version),
            pushed_version=model_version)
