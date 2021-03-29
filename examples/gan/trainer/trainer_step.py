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

import os
from typing import List, Text

import tensorflow as tf

from trainer.gan_functions import Generator, Discriminator, \
    CycleGan, TensorBoardImage
from trainer.gan_functions import discriminator_loss, \
    identity_loss, generator_loss, calc_cycle_loss
from zenml.steps.trainer import TFFeedForwardTrainer
from zenml.utils.naming_utils import check_if_transformed_feature, \
    check_if_transformed_label


class CycleGANTrainer(TFFeedForwardTrainer):
    def __init__(self, batch_size=1, epochs=25, **kwargs):
        self.batch_size = batch_size
        self.epochs = epochs
        super(CycleGANTrainer, self).__init__(batch_size=batch_size,
                                              epochs=epochs,
                                              **kwargs)

    def model_fn(self,
                 train_dataset: tf.data.Dataset,
                 eval_dataset: tf.data.Dataset):
        dataset = tf.data.Dataset.zip((train_dataset, eval_dataset))

        monet_generator_optimizer = tf.keras.optimizers.Adam(2e-4, beta_1=0.5)
        photo_generator_optimizer = tf.keras.optimizers.Adam(2e-4, beta_1=0.5)

        monet_discriminator_optimizer = tf.keras.optimizers.Adam(2e-4,
                                                                 beta_1=0.5)
        photo_discriminator_optimizer = tf.keras.optimizers.Adam(2e-4,
                                                                 beta_1=0.5)

        # transforms photos to Monet paintings
        monet_generator = Generator()
        # transforms Monet paintings to be more like photos
        photo_generator = Generator()

        # differentiates real Monet paintings and generated Monet paintings
        monet_discriminator = Discriminator()
        # differentiates real photos and generated photos
        photo_discriminator = Discriminator()

        cycle_gan_model = CycleGan(
            monet_generator, photo_generator, monet_discriminator,
            photo_discriminator
        )

        cycle_gan_model.compile(
            m_gen_optimizer=monet_generator_optimizer,
            p_gen_optimizer=photo_generator_optimizer,
            m_disc_optimizer=monet_discriminator_optimizer,
            p_disc_optimizer=photo_discriminator_optimizer,
            gen_loss_fn=generator_loss,
            disc_loss_fn=discriminator_loss,
            cycle_loss_fn=calc_cycle_loss,
            identity_loss_fn=identity_loss
        )

        cycle_gan_model.fit(
            dataset,
            batch_size=self.batch_size,
            epochs=self.epochs,
            callbacks=[
                tf.keras.callbacks.TensorBoard(
                    log_dir=os.path.join(self.log_dir, 'train')),
                TensorBoardImage(test_data=eval_dataset,
                                 log_dir=os.path.join(self.log_dir, 'img'))]
        )

        return cycle_gan_model

    def input_fn(self,
                 file_pattern: List[Text]):
        xf_feature_spec = {x: self.schema[x]
                           for x in self.schema
                           if check_if_transformed_feature(x)
                           or check_if_transformed_label(x)}

        return tf.data.experimental.make_batched_features_dataset(
            file_pattern=file_pattern,
            batch_size=self.batch_size,
            shuffle=False,
            num_epochs=1,
            features=xf_feature_spec,
            reader=self._gzip_reader_fn)
