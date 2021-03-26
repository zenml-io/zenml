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


from typing import Dict, List, Text

from zenml.enums import StepTypes
from zenml.steps import BaseStep


class BaseEvaluatorStep(BaseStep):
    """
    Base evaluator step. All evaluator steps should inherit from this class.
    """
    CUSTOM_MODULE = None

    STEP_TYPE = StepTypes.evaluator.name

    def __init__(self,
                 split_mapping: Dict[Text, List[Text]] = None,
                 **kwargs):
        self.split_mapping = split_mapping
        super(BaseEvaluatorStep, self).__init__(split_mapping=split_mapping,
                                                **kwargs)

    def build_config(self):
        pass
