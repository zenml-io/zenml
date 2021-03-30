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
from zenml.steps.trainer.utils import TRAIN_SPLITS, TEST_SPLITS, EVAL_SPLITS


class BaseEvaluatorStep(BaseStep):
    """
    Base evaluator step. All evaluator steps should inherit from this class.
    """
    CUSTOM_MODULE = None

    STEP_TYPE = StepTypes.evaluator.name

    def __init__(self,
                 split_mapping: Dict[Text, List[Text]] = None,
                 **kwargs):

        if split_mapping:
            assert len(split_mapping[TRAIN_SPLITS]) > 0, \
                'While defining your own mapping, you need to provide at least ' \
                'one training split.'
            assert len(split_mapping[EVAL_SPLITS]) > 0, \
                'While defining your own mapping, you need to provide at least ' \
                'one eval split.'

            if TEST_SPLITS not in split_mapping:
                split_mapping.update({TEST_SPLITS: []})
            assert len(split_mapping) == 3, \
                f'While providing a split_mapping please only use ' \
                f'{TRAIN_SPLITS}, {EVAL_SPLITS} and {TEST_SPLITS} as keys.'

            self.split_mapping = split_mapping
        else:
            self.split_mapping = {TRAIN_SPLITS: ['train'],
                                  EVAL_SPLITS: ['eval'],
                                  TEST_SPLITS: ['test']}

        super(BaseEvaluatorStep, self).__init__(split_mapping=split_mapping,
                                                **kwargs)

    def build_config(self):
        pass
