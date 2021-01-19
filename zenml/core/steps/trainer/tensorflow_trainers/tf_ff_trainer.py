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


from typing import List, Text

import tensorflow as tf
import tensorflow_transform as tft

from zenml.core.steps.trainer.tensorflow_trainers.tf_base_trainer import \
    TFBaseTrainerStep


class FeedForwardTrainer(TFBaseTrainerStep):
    """
    Basic Feedforward Neural Network trainer. This step serves as an example
    of how to define your training logic to integrate well with TFX and
    Tensorflow Serving.
    """

    def __init__(self,
                 batch_size: int = 8,
                 lr: float = 0.001,
                 epochs: int = 1,
                 dropout_chance: int = 0.2,
                 loss: str = 'mse',
                 metrics: List[str] = None,
                 hidden_layers: List[int] = None,
                 hidden_activation: str = 'relu',
                 last_activation: str = 'sigmoid',
                 output_units: int = 1,
                 **kwargs):
        """
        Basic feedforward neural network constructor.

        Args:
            batch_size: Input data batch size.
            lr: Learning rate of the optimizer.
            epochs: Number of training epochs (whole passes through the data).
            dropout_chance: Dropout chance, i.e. probability of a neuron not
             propagating its weights into the prediction at a dropout layer.
            loss: Name of the loss function to use.
            metrics: List of metrics to log in training.
            hidden_layers: List of sizes to use in consecutive hidden layers.
             Length determines the number of hidden layers in the network.
            hidden_activation: Name of the activation function to use in the
             hidden layers.
            last_activation: Name of the final activation function creating
             the class probability distribution.
            output_units: Number of output units, corresponding to the number
             of classes.
            **kwargs: Additional keyword arguments.
        """

        self.batch_size = batch_size
        self.lr = lr
        self.epochs = epochs
        self.dropout_chance = dropout_chance
        self.loss = loss
        self.metrics = metrics or []
        self.hidden_layers = hidden_layers or [10]
        self.hidden_activation = hidden_activation
        self.last_activation = last_activation
        self.output_units = output_units

        super(FeedForwardTrainer, self).__init__(
            batch_size=batch_size,
            lr=lr,
            epochs=epochs,
            dropout_chance=dropout_chance,
            loss=loss,
            metrics=metrics,
            hidden_layers=hidden_layers,
            hidden_activation=hidden_activation,
            last_activation=last_activation,
            output_units=output_units,
            **kwargs
        )

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

        xf_feature_spec = {x: xf_feature_spec[x]
                           for x in xf_feature_spec
                           if x.endswith('_xf')}

        dataset = tf.data.experimental.make_batched_features_dataset(
            file_pattern=file_pattern,
            batch_size=self.batch_size,
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
                if f.startswith('label_'):
                    transformed_features.pop(f)
                if not f.endswith('_xf'):
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

            label_spec = [f for f in xf_feature_spec if f.startswith('label_')]
            eval_spec = [f for f in xf_feature_spec if not f.endswith('_xf')]

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

    @staticmethod
    def _gzip_reader_fn(filenames):
        """
        Small utility returning a record reader that can read gzipped files.

        Args:
            filenames: Names of the compressed TFRecord data files.
        """
        return tf.data.TFRecordDataset(filenames, compression_type='GZIP')

    def model_fn(self,
                 train_dataset: tf.data.Dataset,
                 eval_dataset: tf.data.Dataset):
        """
        Function defining the training flow of the feedforward neural network
        model.

        Args:
            train_dataset: tf.data.Dataset containing the training data.
            eval_dataset: tf.data.Dataset containing the evaluation data.

        Returns:
            model: A trained feedforward neural network model.
        """

        train_dataset = train_dataset.batch(self.batch_size,
                                            drop_remainder=True)
        eval_dataset = eval_dataset.batch(self.batch_size, drop_remainder=True)

        features = list(train_dataset.element_spec[0].keys())
        labels = list(train_dataset.element_spec[1].keys())

        input_layers = [tf.keras.layers.Input(shape=(1,), name=k)
                        for k in features]

        d = tf.keras.layers.Concatenate()(input_layers)

        for size in self.hidden_layers:
            d = tf.keras.layers.Dense(size,
                                      activation=self.hidden_activation)(d)
            d = tf.keras.layers.Dropout(self.dropout_chance)(d)

        output_layers = {l: tf.keras.layers.Dense(
            self.output_units,
            activation=self.last_activation,
            name=l)(d) for l in labels}

        model = tf.keras.Model(inputs=input_layers, outputs=output_layers)

        model.compile(loss=self.loss,
                      optimizer=tf.keras.optimizers.Adam(lr=self.lr),
                      metrics=self.metrics)

        model.summary()

        tensorboard_callback = tf.keras.callbacks.TensorBoard(
            log_dir=self.log_dir)

        model.fit(train_dataset,
                  epochs=self.epochs,
                  validation_data=eval_dataset,
                  callbacks=[tensorboard_callback])

        return model
