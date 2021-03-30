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

import pytorch_lightning as pl
import torch
from pytorch_lightning import Trainer
from torch.nn import functional as F

from zenml.steps.trainer import TorchFeedForwardTrainer
from zenml.steps.trainer import utils
from zenml.utils import path_utils


class MyPyTorchLightningTrainer(TorchFeedForwardTrainer):
    """
    PyTorch Lightning trainer
    """

    def run_fn(self):
        train_split_patterns = [self.input_patterns[split] for split in
                                self.split_mapping[utils.TRAIN_SPLITS]]
        train_dataset = self.input_fn(train_split_patterns)

        eval_split_patterns = [self.input_patterns[split] for split in
                               self.split_mapping[utils.EVAL_SPLITS]]
        eval_dataset = self.input_fn(eval_split_patterns)

        class LitModel(pl.LightningModule):
            def __init__(self):
                super().__init__()
                self.l1 = torch.nn.Linear(8, 64)
                self.layer_out = torch.nn.Linear(64, 1)

            def forward(self, x):
                x = torch.relu(self.l1(x))
                x = self.layer_out(x)
                return x

            def training_step(self, batch, batch_idx):
                x, y, z = batch
                x_batch = torch.cat(list(x.values()), dim=-1)
                y_t = torch.cat(list(y.values()), dim=-1)
                y_hat = self(x_batch)
                loss = F.binary_cross_entropy_with_logits(y_hat, y_t)
                tensorboard_logs = {'train_loss': loss}
                return {'loss': loss, 'log': tensorboard_logs}

            def configure_optimizers(self):
                return torch.optim.Adam(self.parameters(), lr=0.001)

            def train_dataloader(self):
                return train_dataset

            def validation_step(self, batch, batch_idx):
                x, y, z = batch
                x_batch = torch.cat(list(x.values()), dim=-1)
                y_t = torch.cat(list(y.values()), dim=-1)
                y_hat = self(x_batch)
                return {
                    'val_loss': F.binary_cross_entropy_with_logits(y_hat, y_t)}

            def validation_epoch_end(self, outputs):
                avg_loss = torch.stack([x['val_loss'] for x in outputs]).mean()
                tensorboard_logs = {'val_loss': avg_loss}
                return {'avg_val_loss': avg_loss, 'log': tensorboard_logs}

            def val_dataloader(self):
                return eval_dataset

        model = LitModel()

        # most basic trainer, uses good defaults
        trainer = Trainer(
            default_root_dir=self.log_dir,
            max_epochs=self.epochs,
        )
        trainer.fit(model)

        path_utils.create_dir_if_not_exists(self.serving_model_dir)
        if path_utils.is_remote(self.serving_model_dir):
            temp_model_dir = '__temp_model_dir__'
            temp_path = os.path.join(os.getcwd(), temp_model_dir)
            if path_utils.is_dir(temp_path):
                raise PermissionError('{} is used as a temp path but it '
                                      'already exists. Please remove it to '
                                      'continue.')
            trainer.save_checkpoint(os.path.join(temp_path, 'model.cpkt'))
            path_utils.copy_dir(temp_path, self.serving_model_dir)
            path_utils.rm_dir(temp_path)
        else:
            trainer.save_checkpoint(
                os.path.join(self.serving_model_dir, 'model.ckpt'))

        # test
        for split in self.split_mapping[utils.TEST_SPLITS]:
            pattern = self.input_patterns[split]
            test_dataset = self.input_fn([pattern])
            test_results = self.test_fn(model, test_dataset)
            utils.save_test_results(test_results, self.output_patterns[split])
