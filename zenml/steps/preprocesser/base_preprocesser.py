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

from typing import Dict, Text, List

from tfx.proto import transform_pb2

from zenml.enums import StepTypes
from zenml.steps import BaseStep
from zenml.steps.trainer.utils import TRAIN_SPLITS

SPLIT_MAPPING = 'split_mapping'


def build_split_mapping(args):
    if SPLIT_MAPPING in args and args[SPLIT_MAPPING]:
        splits_config = transform_pb2.SplitsConfig()
        assert TRAIN_SPLITS in args[SPLIT_MAPPING], \
            f'When you are defining a custom split mapping, please define ' \
            f'{TRAIN_SPLITS}!'
        for process, splits in args[SPLIT_MAPPING].items():
            for split in splits:
                if process == TRAIN_SPLITS:
                    splits_config.analyze.append(split)
                splits_config.transform.append(split)
        return splits_config
    else:
        return None


class BasePreprocesserStep(BaseStep):
    """
    Base class for all preprocessing steps. These steps are used to
    specify transformation and filling operations on data that occur before
    the machine learning model is trained.
    """

    STEP_TYPE = StepTypes.preprocesser.name

    def __init__(self,
                 split_mapping: Dict[Text, List[Text]] = None,
                 **kwargs):
        """
        Base preprocessing step constructor. Custom preprocessing steps need
        to override the `preprocessing_fn` class method.

        Args:
            **kwargs: Additional keyword arguments.
        """

        super(BasePreprocesserStep, self).__init__(split_mapping=split_mapping,
                                                   **kwargs)

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
