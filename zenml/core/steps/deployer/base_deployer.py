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

from zenml.core.steps.base_step import BaseStep


class BaseDeployerStep(BaseStep):
    """
    Base class for all deployer steps. These steps are used to specify a
    configuration for a Pusher component that uploads the model to a selected
    location and opens an endpoint to it from where it serves predictions upon
    request.
    """

    def __init__(self,
                 output_base_dir: Text = None,
                 **kwargs):
        """
        Base deployer step constructor. In order to create custom model
        serving logic, implement deployer steps that inherit from this class.

        Args:
            output_base_dir: Directory where the output model of a
             preceding trainer component was written to.
            **kwargs: Additional keyword arguments.
        """
        self.output_base_dir = output_base_dir

        super(BaseDeployerStep, self).__init__(
            serving_model_dir=output_base_dir,
            **kwargs)
