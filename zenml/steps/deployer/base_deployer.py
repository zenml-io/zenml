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

from typing import Type

from tfx.dsl.components.base import executor_spec
from tfx.dsl.components.base.base_executor import BaseExecutor

from zenml.steps import BaseStep


class BaseDeployerStep(BaseStep):
    """
    Base class for all deployer steps. These steps are used to specify a
    configuration for a Pusher component that uploads the model to a selected
    location and opens an endpoint to it from where it serves predictions upon
    request.
    """

    def __init__(self, **kwargs):
        """
        Base deployer step constructor. In order to create custom model
        serving logic, implement deployer steps that inherit from this class.

        Args:
            **kwargs: Additional keyword arguments.
        """
        super(BaseDeployerStep, self).__init__(**kwargs)

    def get_config(self):
        pass

    def build_push_destination(self):
        pass

    def get_executor(self) -> Type[BaseExecutor]:
        pass

    def _build_pusher_args(self):
        return {'push_destination': self.build_push_destination(),
                'custom_config': self.get_config()}

    def _get_executor_spec(self):
        return executor_spec.ExecutorClassSpec(self.get_executor())
