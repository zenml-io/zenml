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
from typing import List, Text, Dict

import torch
import torch.nn as nn
import torch.optim as optim
import torch.utils.data as data
from torch.utils.tensorboard import SummaryWriter

from zenml.steps.trainer import TorchBaseTrainerStep
from zenml.steps.trainer import utils
from zenml.steps.trainer.pytorch_trainers import utils as torch_utils
from zenml.utils import path_utils


class BinaryClassifier(nn.Module):
    def __init__(self):
        super(BinaryClassifier, self).__init__()
        self.layer_1 = nn.Linear(8, 64)
        self.layer_2 = nn.Linear(64, 64)
        self.layer_out = nn.Linear(64, 1)

        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(p=0.1)
        self.batchnorm1 = nn.BatchNorm1d(64)
        self.batchnorm2 = nn.BatchNorm1d(64)

    def forward(self, inputs):
        x = self.relu(self.layer_1(inputs))
        x = self.batchnorm1(x)
        x = self.relu(self.layer_2(x))
        x = self.batchnorm2(x)
        x = self.dropout(x)
        x = self.layer_out(x)

        return x


def binary_acc(y_pred, y_test):
    y_pred_tag = torch.round(torch.sigmoid(y_pred))
    correct_results_sum = (y_pred_tag == y_test).sum().float()
    acc = correct_results_sum / y_test.shape[0]
    acc = torch.round(acc * 100)

    return acc


class FeedForwardTrainer(TorchBaseTrainerStep):
    def __init__(self,
                 batch_size: int = 32,
                 lr: float = 0.0001,
                 epochs: int = 10,
                 dropout_chance: int = 0.2,
                 loss: str = 'mse',
                 metrics: List[str] = None,
                 hidden_layers: List[int] = None,
                 hidden_activation: str = 'relu',
                 last_activation: str = 'sigmoid',
                 input_units: int = 8,
                 output_units: int = 1,
                 **kwargs):
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

        super(FeedForwardTrainer, self).__init__(
            batch_size=self.batch_size,
            lr=self.lr,
            epochs=self.epochs,
            dropout_chance=self.dropout_chance,
            loss=self.loss,
            metrics=self.metrics,
            hidden_layers=self.hidden_layers,
            hidden_activation=self.hidden_activation,
            last_activation=self.last_activation,
            input_units=self.input_units,
            output_units=self.output_units,
            **kwargs)

    def input_fn(self,
                 file_patterns: List[Text]):

        dataset = torch_utils.TFRecordTorchDataset(file_patterns,
                                                   self.schema)
        loader = torch.utils.data.DataLoader(dataset,
                                             batch_size=self.batch_size,
                                             drop_last=True)
        return loader

    def model_fn(self, train_dataset, eval_dataset):
        return BinaryClassifier()

    def test_fn(self, model, dataset):
        # Activate the evaluation mode
        model.eval()

        batch_list = []
        for x, y, raw in dataset:
            # start with an empty batch
            batch = {}

            # add the raw features with the transformed features and labels
            batch.update(x)
            batch.update(y)
            batch.update(raw)

            # finally, add the output of the model
            x_batch = torch.cat([v for v in x.values()], dim=-1)
            p = model(x_batch)

            if isinstance(p, torch.Tensor):
                batch.update({'output': p})
            elif isinstance(p, dict):
                batch.update(p)
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

        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        model = self.model_fn(train_dataset, eval_dataset)

        model.to(device)
        criterion = nn.BCEWithLogitsLoss()
        optimizer = optim.Adam(model.parameters(), lr=0.001)

        writer = SummaryWriter(self.log_dir)

        model.train()

        total_count = 0

        for e in range(1, self.epochs + 1):
            epoch_loss = 0
            epoch_acc = 0
            step_count = 0
            for x, y, _ in train_dataset:
                step_count += 1
                total_count += 1

                x_batch = torch.cat([v.to(device) for v in x.values()], dim=-1)
                y_batch = torch.cat([v.to(device) for v in y.values()], dim=-1)
                optimizer.zero_grad()

                y_pred = model(x_batch)

                loss = criterion(y_pred, y_batch)
                acc = binary_acc(y_pred, y_batch)

                loss.backward()
                optimizer.step()

                epoch_loss += loss.item()
                epoch_acc += acc.item()

                if e == 1 and step_count == 1:
                    writer.add_graph(model, x_batch)

                writer.add_scalar('training_loss', loss, total_count)
                writer.add_scalar('training_accuracy', acc, total_count)

            print(f'Epoch {e + 0:03}: | Loss: '
                  f'{epoch_loss / step_count:.5f} | Acc: '
                  f'{epoch_acc / step_count:.3f}')

        # test
        for split in self.split_mapping[utils.TEST_SPLITS]:
            assert split in self.input_patterns, \
                f'There are currently no inputs for the split "{split}" ' \
                f'which is currently used in the {utils.TEST_SPLITS} of the ' \
                f'split mapping.'
            pattern = self.input_patterns[split]
            test_dataset = self.input_fn([pattern])
            test_results = self.test_fn(model, test_dataset)
            utils.save_test_results(test_results, self.output_patterns[split])

        path_utils.create_dir_if_not_exists(self.serving_model_dir)
        if path_utils.is_remote(self.serving_model_dir):
            temp_model_dir = '__temp_model_dir__'
            temp_path = os.path.join(os.getcwd(), temp_model_dir)
            if path_utils.is_dir(temp_path):
                raise PermissionError('{} is used as a temp path but it '
                                      'already exists. Please remove it to '
                                      'continue.')
            torch.save(model, temp_path)
            path_utils.copy_dir(temp_path, self.serving_model_dir)
            path_utils.rm_dir(temp_path)
        else:
            torch.save(model, os.path.join(self.serving_model_dir, 'model.pt'))
