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


import os
from typing import Text

from tfx.proto import pusher_pb2

from zenml.core.steps.deployer.base_deployer import BaseDeployerStep


class GCAIPDeployer(BaseDeployerStep):
    """
    Step class for deploying models on Google Cloud AI Platform.
    """

    def __init__(self,
                 project_id: Text,
                 model_name: Text = None,
                 **kwargs):
        """
        Google Cloud AI Platform Deployer Step constructor.

        Use this step to push your trained model to Google Cloud AI Platform,
        where it gets assigned an endpoint that you can query for evaluations
        and predictions.

        Args:
            project_id: Name of the Google Cloud project which the model
             should be pushed to.
            model_name: Name given to the trained model.
            **kwargs: Additional keyword arguments.
        """
        super(GCAIPDeployer, self).__init__(project_id=project_id,
                                            model_name=model_name,
                                            **kwargs)

        self.project_id = project_id
        self.model_name = model_name
        self.serving_model_dir = os.path.join(self.output_base_dir,
                                              'serving_model_dir',
                                              model_name)

    def build_pusher_config(self):
        ai_platform_serving_args = {'model_name': self.model_name,
                                    'project_id': self.project_id}

        destination = pusher_pb2.PushDestination(
            filesystem=pusher_pb2.PushDestination.Filesystem(
                base_directory=self.serving_model_dir))

        return {'push_destination': destination,
                'custom_config': {
                    'ai_platform_serving_args': ai_platform_serving_args}}

    @staticmethod
    def get_executor_spec():
        from tfx.dsl.components.base import executor_spec
        from tfx.extensions.google_cloud_ai_platform.pusher import \
            executor as ai_platform_pusher_executor

        return executor_spec.ExecutorClassSpec(
            ai_platform_pusher_executor.Executor)
