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

from typing import Text

from tfx.extensions.google_cloud_ai_platform.pusher import \
    executor as ai_platform_pusher_executor

from zenml.steps.deployer import BaseDeployerStep
from zenml.logger import get_logger

logger = get_logger(__name__)


class GCAIPDeployer(BaseDeployerStep):
    """
    Step class for deploying models on Google Cloud AI Platform.
    """

    def __init__(self,
                 model_name: Text,
                 project_id: Text,
                 **kwargs):
        """
        Google Cloud AI Platform Deployer Step constructor.

        Use this step to push your trained model to Google Cloud AI Platform,
        where it gets assigned an endpoint that you can query for evaluations
        and predictions.

        Args:
            model_name: Name of the model.
            project_id: Name of the Google Cloud project which the model
             should be pushed to.
             deployment_path: Path where deployment is pushed.
            **kwargs: Additional keyword arguments.
        """
        self.project_id = project_id
        self.model_name = model_name
        logger.warning('When using GCAIPDeployer, please ensure that the '
                       'Artifact Store is a Google Cloud Bucket.')
        super(GCAIPDeployer, self).__init__(project_id=project_id,
                                            model_name=model_name,
                                            **kwargs)

    def get_config(self):
        ai_platform_serving_args = {
            'model_name': self.model_name,
            'project_id': self.project_id
        }
        return {'ai_platform_serving_args': ai_platform_serving_args}

    def get_executor(self):
        return ai_platform_pusher_executor.Executor
