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

from typing import Dict, Text, Optional

from zenml.core.components.pusher import cortex_executor
from zenml.core.steps.deployer.base_deployer import BaseDeployerStep
from zenml.utils.logger import get_logger
from zenml.utils.source_utils import resolve_source_path

logger = get_logger(__name__)


class CortexDeployer(BaseDeployerStep):
    """
    Step class for deploying models using Cortex.
    """

    def __init__(self,
                 api_spec: Dict,
                 predictor=None,
                 requirements=None,
                 conda_packages=None,
                 env: Text = 'aws',
                 project_dir: Optional[str] = None,
                 force: bool = True,
                 wait: bool = False,
                 model_name: Text = '',
                 **kwargs):
        """
        Cortex Deployer Step constructor.

        Use this step to push your trained model to the
        [Cortex API](https://docs.cortex.dev/).

        Args:
            model_name: Name of the model.
            predictor: Cortex Predictor class.
            **kwargs: Additional keyword arguments.
        """
        if conda_packages is None:
            conda_packages = []
        if requirements is None:
            requirements = []

        self.model_name = model_name
        self.env = env
        self.predictor = predictor
        self.api_spec = api_spec
        self.requirements = requirements
        self.project_dir = project_dir
        self.conda_packages = conda_packages
        self.force = force
        self.wait = wait
        super(CortexDeployer, self).__init__(
            model_name=model_name,
            env=self.env,
            predictor=predictor,
            api_spec=self.api_spec,
            requirements=self.requirements,
            project_dir=self.project_dir,
            conda_packages=self.conda_packages,
            force=self.force,
            wait=self.wait,
            **kwargs)

    def get_config(self):
        return {
            "cortex_serving_args": {
                "env": self.env,
                "api_spec": self.api_spec,
                "predictor_path": resolve_source_path(
                    self.predictor.__module__ + '.' + self.predictor.__name__
                ),
                "requirements": self.requirements,
                "conda_packages": self.conda_packages,
                "project_dir": self.project_dir,
                "force": self.force,
                "wait": self.wait,
            }}

    def get_executor(self):
        return cortex_executor.Executor
