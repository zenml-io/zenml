#  Copyright (c) maiot GmbH 2021. All Rights Reserved.
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

import tensorflow_transform as tft
import tensorflow as tf
from typing import List, Text
from zenml.core.steps.trainer.tensorflow_trainers.tf_base_trainer import \
    TFBaseTrainerStep
from transformers import TFBertForSequenceClassification


class UrduTrainer(TFBaseTrainerStep):
    def __init__(self,
                 serving_model_dir: Text = None,
                 transform_output: Text = None,
                 train_files: List[Text] = None,
                 eval_files: List[Text] = None,
                 batch_size: int = 64,
                 epochs: int = 25,
                 ):

        super(UrduTrainer, self).__init__(serving_model_dir=serving_model_dir,
                                          transform_output=transform_output,
                                          train_files=train_files,
                                          eval_files=eval_files,
                                          batch_size=batch_size,
                                          epochs=epochs)

        self.batch_size = batch_size
        self.epochs = epochs

    def get_run_fn(self):
        return self.run_fn

    def run_fn(self):
        tf_transform_output = tft.TFTransformOutput(self.transform_output)

        train_dataset = self.input_fn(self.train_files, tf_transform_output)
        eval_dataset = self.input_fn(self.eval_files, tf_transform_output)

        model = self.model_fn(train_dataset=train_dataset,
                              eval_dataset=eval_dataset)

        signatures = {
            'serving_default':
                self._get_serve_tf_examples_fn(
                    model,
                    tf_transform_output
                ).get_concrete_function(tf.TensorSpec(shape=[None],
                                                      dtype=tf.string,
                                                      name='examples')),
            'zen_eval':
                self._get_zen_eval_tf_examples_fn(
                    model,
                    tf_transform_output
                ).get_concrete_function(tf.TensorSpec(shape=[None],
                                                      dtype=tf.string,
                                                      name='examples'))}

        model.save(self.serving_model_dir,
                   save_format='tf',
                   signatures=signatures)

    def model_fn(self,
                 train_dataset: tf.data.Dataset,
                 eval_dataset: tf.data.Dataset):

        model = TFBertForSequenceClassification.from_pretrained(
            'bert-base-uncased', num_labels=2)

        optimizer = tf.keras.optimizers.Adam(learning_rate=3e-5)
        loss = tf.keras.losses.BinaryCrossentropy(from_logits=True)

        model.compile(optimizer=optimizer, loss=loss)

        model.train(train_dataset, epochs=self.epochs)

        return model

    def input_fn(self,
                 file_pattern: List[Text],
                 tf_transform_output: tft.TFTransformOutput):
        """
        Feedforward input_fn for loading data from TFRecords saved to a
        location on disk.

        Args:
            file_pattern: File pattern matching saved TFRecords on disk.
            tf_transform_output: Output of the preceding Transform /
             Preprocessing component.

        Returns:
            dataset: tf.data.Dataset created out of the input files.
        """

        xf_feature_spec = tf_transform_output.transformed_feature_spec()

        dataset = tf.data.experimental.make_batched_features_dataset(
            file_pattern=file_pattern,
            batch_size=self.batch_size,
            features=xf_feature_spec,
            label_key="label",
            reader=self._gzip_reader_fn,
            num_epochs=1)

        dataset = dataset.unbatch()

        return dataset

    @staticmethod
    def _gzip_reader_fn(filenames):
        """
        Small utility returning a record reader that can read gzipped files.

        Args:
            filenames: Names of the compressed TFRecord data files.
        """
        return tf.data.TFRecordDataset(filenames, compression_type='GZIP')

    @staticmethod
    def _get_serve_tf_examples_fn(model, tf_transform_output):
        """
        Returns a function that parses a serialized tf.Example for prediction.

        Args:
            model: Trained model, output of the model_fn.
            tf_transform_output: Output of the preceding Transform /
             Preprocessing component.
        """

        model.tft_layer = tf_transform_output.transform_features_layer()

        @tf.function
        def serve_tf_examples_fn(serialized_tf_examples):
            """Returns the output to be used in the serving signature."""
            raw_feature_spec = tf_transform_output.raw_feature_spec()
            parsed_features = tf.io.parse_example(serialized_tf_examples,
                                                  raw_feature_spec)

            xf_feature_spec = tf_transform_output.transformed_feature_spec()
            transformed_features = model.tft_layer(parsed_features)
            for f in xf_feature_spec:
                if f == "label":
                    transformed_features.pop(f)
                if f not in ["news", "category", "tokens", "ids"]:
                    transformed_features.pop(f)

            return model(transformed_features)

        return serve_tf_examples_fn

    @staticmethod
    def _get_zen_eval_tf_examples_fn(model, tf_transform_output):
        """
        Returns a function that parses a serialized tf.Example for
        evaluation.

        Args:
            model: Trained model, output of the model_fn.
            tf_transform_output: Output of the preceding Transform /
             Preprocessing component.
        """

        model.tft_layer = tf_transform_output.transform_features_layer()

        @tf.function
        def zen_eval_tf_examples_fn(serialized_tf_examples):
            """Returns the output to be used in the ce_eval signature."""
            xf_feature_spec = tf_transform_output.transformed_feature_spec()

            label_spec = [f for f in xf_feature_spec if f == "label"]
            eval_spec = [f for f in xf_feature_spec if not f == "label"]

            transformed_features = tf.io.parse_example(serialized_tf_examples,
                                                       xf_feature_spec)

            for f in label_spec + eval_spec:
                transformed_features.pop(f)

            outputs = model(transformed_features)

            if isinstance(outputs, dict):
                return outputs
            elif isinstance(outputs, list):
                return {o.name.split("/")[1]: o for o in outputs}
            elif isinstance(outputs, tf.Tensor):
                return {outputs.name.split("/")[1]: outputs}

        return zen_eval_tf_examples_fn
