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


from typing import List

import tensorflow as tf

from zenml.steps.trainer import TFFeedForwardTrainer
from zenml.steps.trainer import utils
from zenml.utils import naming_utils


class ImageTensorflowTrainer(TFFeedForwardTrainer):
    """Generic Trainer for Images"""

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

        super(ImageTensorflowTrainer, self).__init__(
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

    def test_fn(self, model, dataset):
        batch_list = []
        for x, y in dataset:
            # start with an empty batch
            batch = {}

            transformed_f = {f: x[f] for f in x if
                             naming_utils.check_if_transformed_feature(f)}
            raw_f = {f: x[f] for f in x if
                     not naming_utils.check_if_transformed_feature(f)}

            # add the raw features with the transformed features and labels
            batch.update(transformed_f)
            batch.update(y)
            batch.update(raw_f)

            # finally, add the output of the
            p = model.predict(x)

            if isinstance(p, tf.Tensor):
                batch.update({'output': p})
            elif isinstance(p, dict):
                batch.update({naming_utils.output_name(k): p[k] for k in p})
            elif isinstance(p, list):
                batch.update(
                    {'output_{}'.format(i): v for i, v in enumerate(p)})
            else:
                raise TypeError('Unknown output format!')

            batch_list.append(batch)

        combined_batch = utils.combine_batch_results(batch_list)

        return combined_batch

    def run_fn(self):
        train_split_patterns = [self.input_patterns[split] for split in
                                self.split_mapping[utils.TRAIN_SPLITS]]
        train_dataset = self.input_fn(train_split_patterns)

        eval_split_patterns = [self.input_patterns[split] for split in
                               self.split_mapping[utils.EVAL_SPLITS]]
        eval_dataset = self.input_fn(eval_split_patterns)

        model = self.model_fn(train_dataset=train_dataset,
                              eval_dataset=eval_dataset)

        for split in self.split_mapping[utils.TEST_SPLITS]:
            assert split in self.input_patterns, \
                f'There are currently no inputs for the split "{split}" ' \
                f'which is currently used in the {utils.TEST_SPLITS} of the ' \
                f'split mapping.'
            pattern = self.input_patterns[split]
            test_dataset = self.input_fn([pattern])
            test_results = self.test_fn(model, test_dataset)
            utils.save_test_results(test_results, self.output_patterns[split])

        signatures = {
            'serving_default':
                self._get_serve_tf_examples_fn(
                    model,
                    self.tf_transform_output
                ).get_concrete_function(tf.TensorSpec(shape=[None],
                                                      dtype=tf.string,
                                                      name='examples')),
            'zen_eval':
                self._get_zen_eval_tf_examples_fn(
                    model,
                    self.tf_transform_output
                ).get_concrete_function(tf.TensorSpec(shape=[None],
                                                      dtype=tf.string,
                                                      name='examples'))}

        model.save(self.serving_model_dir,
                   save_format='tf',
                   signatures=signatures)

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
        # features = list(train_dataset.element_spec[0].keys())
        # labels = list(train_dataset.element_spec[1].keys())
        input = tf.keras.layers.Input(shape=(28, 28, 3), name='image_xf')
        x = tf.keras.layers.Conv2D(32, kernel_size=(3, 3), activation="relu")(
            input)
        x = tf.keras.layers.MaxPooling2D(pool_size=(2, 2))(x)
        x = tf.keras.layers.Conv2D(64, kernel_size=(3, 3), activation="relu")(
            x)
        x = tf.keras.layers.MaxPooling2D(pool_size=(2, 2))(x)
        x = tf.keras.layers.Flatten()(x)
        x = tf.keras.layers.Dropout(0.5)(x)
        x = tf.keras.layers.Dense(1, name='label_xl', activation="softmax")(x)

        model = tf.keras.Model(inputs=input, outputs=x)

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
