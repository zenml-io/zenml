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
import os

import tensorflow as tf
import tensorflow_transform as tft
import torch
import torch.nn as nn
import torch.optim as optim
import torch.utils.data as data

from zenml.core.steps.trainer.base_trainer import BaseTrainerStep
from zenml.utils import path_utils
from zenml.utils.post_training.post_training_utils import \
    convert_raw_dataset_to_pandas


"""
TODO:
    * Currently, we convert TFRecords to Pandas by loading them in first. Not 
    optimal. We should use a native interface to TFRecords, such as this 
    library does: https://github.com/vahidk/tfrecord . We can use the library 
    or use some of the logic in it for our use-case.
    * PyTorchDataset expects a Pandas DataFrame. Should expect a TFRecords.
    * Once all this is done, we should provide a nice interface similar to 
    FeedForwardTrainer. I would advocate to rename FeedForwardTrainerStep to
    TensorflowTrainerStep and this to PyTorchStep so that they are the base 
    steps to inherit from for these libraries. We can make a sci-kit learn one 
    as well.
"""

class PyTorchDataset(data.Dataset):
    """Face Landmarks dataset."""

    def __init__(self, df):
        """
        Args:
        """
        self.df = df

    def __len__(self):
        # print len(self.landmarks_frame)
        # return len(self.landmarks_frame)
        return self.df.shape[0]

    def __getitem__(self, idx):
        if torch.is_tensor(idx):
            idx = idx.tolist()
        all_data = self.df.iloc[idx, :].to_dict()
        X_data = [v for k, v in all_data.items() if k.endswith('_xf')]
        Y_data = [v for k, v in all_data.items() if k.startswith('label_')]

        return torch.FloatTensor(X_data), torch.FloatTensor(Y_data)[0]


def binary_acc(y_pred, y_test):
    y_pred_tag = torch.round(torch.sigmoid(y_pred))

    correct_results_sum = (y_pred_tag == y_test).sum().float()
    acc = correct_results_sum / y_test.shape[0]
    acc = torch.round(acc * 100)

    return acc


class binaryClassification(nn.Module):
    def __init__(self):
        super(binaryClassification, self).__init__()
        # Number of input features is 12.
        self.layer_1 = nn.Linear(9, 64)
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


class PyTorchTrainer(BaseTrainerStep):
    def __init__(self,
                 batch_size: int = 8,
                 lr: float = 0.0001,
                 epochs: int = 50,
                 dropout_chance: int = 0.2,
                 loss: str = 'mse',
                 metrics: List[str] = None,
                 hidden_layers: List[int] = None,
                 hidden_activation: str = 'relu',
                 last_activation: str = 'sigmoid',
                 input_units: int = 9,
                 output_units: int = 1,
                 serving_model_dir: Text = None,
                 transform_output: Text = None,
                 train_files: Text = None,
                 eval_files: Text = None,
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
        super().__init__(**kwargs)
        self.serving_model_dir = serving_model_dir
        self.transform_output = transform_output
        self.train_files = train_files
        self.eval_files = eval_files

    def get_pytorch_dataset(self, files):
        tf_transform_output = tft.TFTransformOutput(self.transform_output)
        spec = tf_transform_output.transformed_feature_spec()
        train_files = files.replace("*", "")
        data_files = path_utils.list_dir(train_files)
        dataset = tf.data.TFRecordDataset(data_files, compression_type='GZIP')
        sample_size = 10000
        df = convert_raw_dataset_to_pandas(dataset, spec, sample_size)
        dataset = PyTorchDataset(df)
        loader = torch.utils.data.DataLoader(
            dataset, batch_size=self.batch_size, shuffle=True)
        data = next(iter(loader))
        print(data)
        return loader

    def run_fn(self):
        # do my own thing here
        train_loader = self.get_pytorch_dataset(self.train_files[0])
        eval_loader = self.get_pytorch_dataset(self.eval_files[0])

        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        print(device)
        model = binaryClassification()
        model.to(device)
        print(model)
        criterion = nn.BCEWithLogitsLoss()
        optimizer = optim.Adam(model.parameters(), lr=0.001)

        model.train()
        for e in range(1, self.epochs + 1):
            epoch_loss = 0
            epoch_acc = 0
            for X_batch, y_batch in train_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                optimizer.zero_grad()

                y_pred = model(X_batch)

                loss = criterion(y_pred, y_batch.unsqueeze(1))
                acc = binary_acc(y_pred, y_batch.unsqueeze(1))

                loss.backward()
                optimizer.step()

                epoch_loss += loss.item()
                epoch_acc += acc.item()

            print(
                f'Epoch {e + 0:03}: | Loss: '
                f'{epoch_loss / len(train_loader):.5f} | Acc: '
                f'{epoch_acc / len(train_loader):.3f}')

        path_utils.create_dir_if_not_exists(self.serving_model_dir)
        torch.save(model, os.path.join(self.serving_model_dir, 'model.pt'))
