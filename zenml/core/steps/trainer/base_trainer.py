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
from typing import List, Text

import tensorflow as tf
import tensorflow_transform as tft

from zenml.core.steps.base_step import BaseStep
from zenml.utils.enums import StepTypes


class BaseTrainerStep(BaseStep):
    STEP_TYPE = StepTypes.trainer.name

    def __init__(self,
                 serving_model_dir: Text = None,
                 transform_output: Text = None,
                 train_files=None,
                 eval_files=None,
                 **kwargs):
        """
        Constructor for BaseTrainerStep.

        Args:
            serving_model_dir:
            transform_output:
            train_files:
            eval_files:
            log_dir:
            schema:
        """
        super().__init__(**kwargs)
        self.serving_model_dir = serving_model_dir
        self.transform_output = transform_output
        self.train_files = train_files
        self.eval_files = eval_files
        self.schema = None
        self.log_dir = None

        # Infer schema and log_dir
        if self.transform_output is not None:
            tf_transform_output = tft.TFTransformOutput(self.transform_output)
            self.schema = tf_transform_output.transformed_feature_spec().copy()

        if self.serving_model_dir is not None:
            self.log_dir = os.path.join(
                os.path.dirname(self.serving_model_dir), 'logs')

    def get_run_fn(self):
        return self.run_fn

    def run_fn(self):
        pass

    def input_fn(self,
                 file_pattern: List[Text],
                 tf_transform_output: tft.TFTransformOutput):
        pass

    @staticmethod
    def _get_serve_tf_examples_fn(model, tf_transform_output):
        pass

    @staticmethod
    def _get_ce_eval_tf_examples_fn(model, tf_transform_output):
        pass

    @staticmethod
    def model_fn(train_dataset: tf.data.Dataset,
                 eval_dataset: tf.data.Dataset):
        pass
