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

# TODO: Timeseries input preparation is problematic

import os
from typing import List, Text, Dict

import tensorflow as tf
import tensorflow_transform as tft

from zenml.core.steps.base_step import BaseStep


class TrainerStep(BaseStep):
    def __init__(self, config):
        self.serving_model_dir = config['serving_model_dir']
        self.transform_output = config['transform_output']
        self.train_files = config['train_files']
        self.eval_files = config['eval_files']

        self.model_params = config['params']

    def get_run_fn(self):
        return self.run_fn

    def run_fn(self):
        log_dir = os.path.join(os.path.dirname(self.serving_model_dir),
                               'logs')

        tf_transform_output = tft.TFTransformOutput(self.transform_output)
        schema = tf_transform_output.transformed_feature_spec().copy()

        train_dataset = self.input_fn(self.train_files, tf_transform_output)
        eval_dataset = self.input_fn(self.eval_files, tf_transform_output)

        model = self.model_fn(train_dataset=train_dataset,
                              eval_dataset=eval_dataset,
                              schema=schema,
                              log_dir=log_dir,
                              **self.model_params)

        signatures = {
            'serving_default':
                self._get_serve_tf_examples_fn(
                    model,
                    tf_transform_output
                ).get_concrete_function(tf.TensorSpec(shape=[None],
                                                      dtype=tf.string,
                                                      name='examples')),
            'ce_eval':
                self._get_ce_eval_tf_examples_fn(
                    model,
                    tf_transform_output
                ).get_concrete_function(tf.TensorSpec(shape=[None],
                                                      dtype=tf.string,
                                                      name='examples'))}

        model.save(self.serving_model_dir,
                   save_format='tf',
                   signatures=signatures)

    def input_fn(self,
                 file_pattern: List[Text],
                 tf_transform_output: tft.TFTransformOutput):

        xf_feature_spec = tf_transform_output.transformed_feature_spec()

        xf_feature_spec = {x: xf_feature_spec[x]
                           for x in xf_feature_spec
                           if x.endswith('_xf')}

        dataset = tf.data.experimental.make_batched_features_dataset(
            file_pattern=file_pattern,
            batch_size=32,
            features=xf_feature_spec,
            reader=self._gzip_reader_fn,
            num_epochs=1)

        dataset = dataset.unbatch()

        def split_inputs_labels(x):
            inputs = {}
            labels = {}
            for e in x:
                if not e.startswith('label'):
                    inputs[e] = x[e]
                else:
                    labels[e] = x[e]

            labels = {
                label[len('label_'):-len('_xf')]:
                    labels[label]
                for label in labels.keys()
            }

            return inputs, labels

        dataset = dataset.map(split_inputs_labels)

        return dataset

    @staticmethod
    def _get_serve_tf_examples_fn(model, tf_transform_output):
        """Returns a function that parses a serialized tf.Example.

        Args:
            model:
            tf_transform_output:
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
                if f.startswith('label_'):
                    transformed_features.pop(f)
                if not f.endswith('_xf'):
                    transformed_features.pop(f)

            return model(transformed_features)

        return serve_tf_examples_fn

    @staticmethod
    def _get_ce_eval_tf_examples_fn(model, tf_transform_output):
        """Returns a function that parses a serialized tf.Example.

        Args:
            model:
            tf_transform_output:
        """

        model.tft_layer = tf_transform_output.transform_features_layer()

        @tf.function
        def ce_eval_tf_examples_fn(serialized_tf_examples):
            """Returns the output to be used in the ce_eval signature."""
            xf_feature_spec = tf_transform_output.transformed_feature_spec()

            label_spec = [f for f in xf_feature_spec if f.startswith('label_')]
            eval_spec = [f for f in xf_feature_spec if not f.endswith('_xf')]

            transformed_features = tf.io.parse_example(serialized_tf_examples,
                                                       xf_feature_spec)

            for f in label_spec + eval_spec:
                transformed_features.pop(f)

            outputs = model(transformed_features)

            if isinstance(outputs, dict):
                if len(outputs) == 1:
                    return list(outputs.values())[0]

                raw_label_spec = [
                    l[len('label_'):-len('_xf')]
                    for l in label_spec]
                assert set(outputs.keys()) == set(raw_label_spec), \
                    'While you create the model, make sure that the output ' \
                    'names {} are the same with your selected labels {}.'.format(
                        set(outputs.keys()), set(raw_label_spec))

                print({'output_{}'.format(i + 1): outputs[k]
                       for i, k in enumerate(sorted(list(outputs.keys())))})
                return {'output_{}'.format(i + 1): outputs[k]
                        for i, k in enumerate(sorted(list(outputs.keys())))}

            elif isinstance(outputs, list):
                if len(outputs) == 1:
                    return outputs[0]

                names = {o.name.split("/")[1]: o for o in outputs}

                raw_label_spec = [
                    l[len('label_'):-len('_xf')]
                    for l in label_spec]
                assert set(names.keys()) == set(raw_label_spec), \
                    'While you create the model, make sure that the output ' \
                    'names {} are the same with your selected labels {}.'.format(
                        set(names.keys()), set(raw_label_spec))

                return {'output_{}'.format(i + 1): names[k]
                        for i, k in enumerate(sorted(list(names.keys())))}

            elif isinstance(outputs, tf.Tensor):
                return outputs

            else:
                raise ValueError(
                    'When you are defining your model, please define '
                    'your output label as a dict, list or a single '
                    'Tensor.')

        return ce_eval_tf_examples_fn

    @staticmethod
    def _gzip_reader_fn(filenames):
        """Small utility returning a record reader that can read gzip'ed files.

        Args:
            filenames:
        """
        return tf.data.TFRecordDataset(filenames, compression_type='GZIP')

    @staticmethod
    def model_fn(train_dataset: tf.data.Dataset,
                 eval_dataset: tf.data.Dataset,
                 schema: Dict,
                 log_dir: str,
                 batch_size: int = 32,
                 lr: float = 0.0001,
                 epochs: int = 10,
                 dropout_chance: int = 0.2,
                 loss: str = 'mse',
                 metrics: List[str] = None,
                 hidden_layers: List[int] = None,
                 hidden_activation: str = 'relu',
                 last_activation: str = 'sigmoid',
                 input_units: int = 11,
                 output_units: int = 1,
                 ):
        """returns: a Tensorflow/Keras model

        Args:
            train_dataset (tf.data.Dataset):
            eval_dataset (tf.data.Dataset):
            schema (Dict):
            log_dir (str):
            batch_size (int):
            lr (float):
            epochs (int):
            dropout_chance (int):
            loss (str):
            metrics:
            hidden_layers:
            hidden_activation (str):
            last_activation (str):
            input_units (int):
            output_units (int):
        """
        train_dataset = train_dataset.batch(batch_size, drop_remainder=True)
        eval_dataset = eval_dataset.batch(batch_size, drop_remainder=True)

        if metrics is None:
            metrics = []

        if hidden_layers is None:
            hidden_layers = [64, 32, 16]

        input_layers = [tf.keras.layers.Input(shape=(1,), name=k)
                        for k in train_dataset.element_spec[0].keys()]
        d = tf.keras.layers.Concatenate()(input_layers)

        for size in hidden_layers:
            d = tf.keras.layers.Dense(size, activation=hidden_activation)(d)
            d = tf.keras.layers.Dropout(dropout_chance)(d)

        output_layer = tf.keras.layers.Dense(output_units,
                                             activation=last_activation,
                                             name='tips')(d)

        model = tf.keras.Model(inputs=input_layers,
                               outputs=output_layer)

        model.compile(loss=loss,
                      optimizer=tf.keras.optimizers.Adam(lr=lr),
                      metrics=metrics)

        model.summary()

        tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir=log_dir)

        model.fit(train_dataset,
                  epochs=epochs,
                  validation_data=eval_dataset,
                  callbacks=[tensorboard_callback])

        return model
