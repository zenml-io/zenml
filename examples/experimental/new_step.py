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

from zenml.core.steps.trainer.feedforward_trainer import FeedForwardTrainer


class MyTrainer(FeedForwardTrainer):
    def __init__(self,
                 batch_size: int = 8,
                 lr: float = 0.0001,
                 epochs: int = 1,
                 dropout_chance: int = 0.2,
                 loss: str = 'mse',
                 metrics: List[str] = None,
                 hidden_layers: List[int] = None,
                 hidden_activation: str = 'relu',
                 last_activation: str = 'sigmoid',
                 input_units: int = 11,
                 output_units: int = 1,
                 my_param1: int = 10,
                 **kwargs
                 ):
        self.batch_size = batch_size
        self.lr = lr
        self.epochs = epochs
        self.dropout_chance = dropout_chance
        self.loss = loss
        self.metrics = metrics or []
        self.hidden_layers = hidden_layers or [64, 32, 16]
        self.hidden_activation = hidden_activation
        self.last_activation = last_activation
        self.input_units = input_units
        self.output_units = output_units
        self.my_param1 = my_param1
        super().__init__(**kwargs)

    def model_fn(self,
                 train_dataset: tf.data.Dataset,
                 eval_dataset: tf.data.Dataset):
        train_dataset = train_dataset.batch(self.batch_size,
                                            drop_remainder=True)
        eval_dataset = eval_dataset.batch(self.batch_size, drop_remainder=True)

        input_layers = [tf.keras.layers.Input(shape=(1,), name=k)
                        for k in train_dataset.element_spec[0].keys()]
        d = tf.keras.layers.Concatenate()(input_layers)

        for size in self.hidden_layers:
            d = tf.keras.layers.Dense(size,
                                      activation=self.hidden_activation)(d)
            d = tf.keras.layers.Dropout(self.dropout_chance)(d)

        output_layer = tf.keras.layers.Dense(self.output_units,
                                             activation=self.last_activation,
                                             name='tips')(d)

        model = tf.keras.Model(inputs=input_layers,
                               outputs=output_layer)

        model.compile(loss=self.loss,
                      optimizer=tf.keras.optimizers.Adam(lr=self.lr),
                      metrics=self.metrics)

        model.summary()

        tensorboard_callback = tf.keras.callbacks.TensorBoard(
            log_dir=self.log_dir)

        model.fit(train_dataset,
                  steps_per_epoch=2,
                  epochs=self.epochs,
                  validation_data=eval_dataset,
                  callbacks=[tensorboard_callback])

        return model
