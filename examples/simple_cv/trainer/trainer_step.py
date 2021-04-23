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
                 loss: str = 'mse',
                 metrics: List[str] = None,
                 hidden_activation: str = 'relu',
                 last_activation: str = 'sigmoid',
                 **kwargs):
        """
        Basic feedforward neural network constructor.

        Args:
            batch_size: Input data batch size.
            lr: Learning rate of the optimizer.
            epochs: Number of training epochs (whole passes through the data).
            metrics: List of metrics to log in training.
            hidden_layers: List of sizes to use in consecutive hidden layers.
             Length determines the number of hidden layers in the network.
            hidden_activation: Name of the activation function to use in the
             hidden layers.
            last_activation: Name of the final activation function creating
             the class probability distribution.

            **kwargs: Additional keyword arguments.
        """

        self.batch_size = batch_size
        self.lr = lr
        self.epochs = epochs
        self.loss = loss
        self.metrics = metrics or []
        self.hidden_activation = hidden_activation
        self.last_activation = last_activation

        super(ImageTensorflowTrainer, self).__init__(
            batch_size=batch_size,
            lr=lr,
            epochs=epochs,
            loss=loss,
            metrics=metrics,
            hidden_activation=hidden_activation,
            last_activation=last_activation,
            **kwargs
        )

    def run_fn(self):
        train_split_patterns = [self.input_patterns[split] for split in
                                self.split_mapping[utils.TRAIN_SPLITS]]
        train_dataset = self.input_fn(train_split_patterns)

        eval_split_patterns = [self.input_patterns[split] for split in
                               self.split_mapping[utils.EVAL_SPLITS]]
        eval_dataset = self.input_fn(eval_split_patterns)

        model = self.model_fn(train_dataset=train_dataset,
                              eval_dataset=eval_dataset)

        signatures = self.get_signatures(model)

        model.save(
            self.serving_model_dir, save_format='tf', signatures=signatures)

    def model_fn(self,
                 train_dataset: tf.data.Dataset,
                 eval_dataset: tf.data.Dataset):
        """
        Simple function that defines a CNN for MNIST.

        Args:
            train_dataset: tf.data.Dataset containing the training data.
            eval_dataset: tf.data.Dataset containing the evaluation data.

        Returns:
            model: A trained feedforward neural network model.
        """
        features = list(train_dataset.element_spec[0].keys())
        labels = list(train_dataset.element_spec[1].keys())

        features = [k for k in features if
                    naming_utils.check_if_transformed_feature(k)]
        full_shape = train_dataset.element_spec[0][features[0]].shape

        input = tf.keras.layers.Input(shape=full_shape[1:], name=features[0])
        x = tf.keras.layers.Conv2D(16, kernel_size=(3, 3), activation="relu")(
            input)
        x = tf.keras.layers.MaxPooling2D(pool_size=(2, 2))(x)
        x = tf.keras.layers.Flatten()(x)
        x = tf.keras.layers.Dense(1, name=labels[0])(x)

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
