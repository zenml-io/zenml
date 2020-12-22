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

from typing import Dict

from zenml.core.steps.base_step import BaseStep
from zenml.utils.enums import StepTypes


class BasePreprocesserStep(BaseStep):
    """
    Base class for all preprocessing steps. These steps are used to
    specify transformation and filling operations on data that occur before
    the machine learning model is trained.
    """

    STEP_TYPE = StepTypes.preprocesser.name

    def __init__(self, **kwargs):
        """
        Base preprocessing step constructor. Custom preprocessing steps need
        to override the `preprocessing_fn` class method.

        Args:
            **kwargs: Additional keyword arguments.
        """

        super().__init__(**kwargs)

    def get_preprocessing_fn(self):
        return self.preprocessing_fn

    def preprocessing_fn(self, inputs: Dict):
        """
        Function used in the Transform component. Override this to do custom
        preprocessing logic.

        Args:
            inputs (dict): Inputs where keys are feature names and values are
            tensors which represent the values of the features.

        Returns:
            outputs (dict): Inputs where keys are transformed feature names
             and values are tensors with the transformed values of the
             features.
        """
        pass
