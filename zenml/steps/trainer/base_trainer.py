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

import tensorflow_transform as tft

from zenml.enums import StepTypes
from zenml.steps import BaseStep


class BaseTrainerStep(BaseStep):
    """
    Base step interface for all Trainer steps. All of your code concerning
    model training should leverage subclasses of this class.
    """

    STEP_TYPE = StepTypes.trainer.name

    def __init__(self,
                 serving_model_dir: Text = None,
                 transform_output: Text = None,
                 test_results: Text = None,
                 train_files=None,
                 eval_files=None,
                 **kwargs):
        """
        Constructor for the BaseTrainerStep. All subclasses used for custom
        training of user machine learning models should implement the `run_fn`
        `model_fn` and `input_fn` methods used for control flow, model training
        and input data preparation, respectively.

        Args:
            serving_model_dir: Directory indicating where to save the trained
             model.
            transform_output: Output of a preceding transform component.
            train_files: String, file pattern of the location of TFRecords for
             model training. Intended for use in the input_fn.
            eval_files: String, file pattern of the location of TFRecords for
             model evaluation. Intended for use in the input_fn.
            log_dir: Logs output directory.
            schema: Schema file from a preceding SchemaGen.
        """
        super().__init__(**kwargs)
        self.serving_model_dir = serving_model_dir
        self.transform_output = transform_output
        self.test_results = test_results
        self.train_files = train_files
        self.eval_files = eval_files
        self.schema = None
        self.log_dir = None
        self.tf_transform_output = None

        # Infer schema and log_dir
        if self.transform_output is not None:
            self.tf_transform_output = tft.TFTransformOutput(
                self.transform_output)
            self.schema = self.tf_transform_output.transformed_feature_spec(

            ).copy()

        if self.serving_model_dir is not None:
            self.log_dir = os.path.join(
                os.path.dirname(self.serving_model_dir), 'logs')

    def input_fn(self,
                 file_pattern: List[Text],
                 tf_transform_output: tft.TFTransformOutput):
        """
        Method for loading data from TFRecords saved to a location on
        disk. Override this method in subclasses to define your own custom
        data preparation flow.

        Args:
            file_pattern: File pattern matching saved TFRecords on disk.
            tf_transform_output: Output of the preceding Transform /
             Preprocessing component.

        Returns:
            dataset: A tf.data.Dataset constructed from the input file
             pattern and transform.
        """
        pass

    @staticmethod
    def model_fn(train_dataset,
                 eval_dataset):
        """
        Method defining the training flow of the model. Override this
        in subclasses to define your own custom training flow.

        Args:
            train_dataset: tf.data.Dataset containing the training data.
            eval_dataset: tf.data.Dataset containing the evaluation data.

        Returns:
            model: A trained machine learning model.
        """
        pass

    def run_fn(self):
        """
        Method defining the control flow of the training process inside
        the TFX Trainer Component Executor. Override this method in subclasses
        to define your own custom training flow.
        """
        pass

    def test_fn(self, *args, **kwargs):
        """
        Optional method for defining a test flow of the model. The goal of
        this method is to give the user an interface to provide a testing
        function, where the results (if given in the right format with
        features, labels and predictions) will be ultimately saved to
        disk using an output artifact. Once defined, it allows the user to
        utilize the model agnostic evaluator in their training pipeline.
        """
        pass
