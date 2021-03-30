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
from typing import List, Text, Dict

import tensorflow as tf
from transformers import TFDistilBertForSequenceClassification

from zenml.steps.trainer import TFBaseTrainerStep
from zenml.utils.post_training.post_training_utils import \
    get_feature_spec_from_schema
from zenml.steps.trainer import utils


class UrduTrainer(TFBaseTrainerStep):
    def __init__(self,
                 model_name: Text,
                 batch_size: int = 64,
                 epochs: int = 25,
                 learning_rate: float = 1e-4,
                 schema_file: Text = None,
                 **kwargs
                 ):

        super(UrduTrainer, self).__init__(model_name=model_name,
                                          batch_size=batch_size,
                                          epochs=epochs,
                                          learning_rate=learning_rate,
                                          **kwargs)

        # ML variables
        self.batch_size = batch_size
        self.epochs = epochs
        self.learning_rate = learning_rate
        self.model_name = model_name

        if schema_file:
            self.schema_path = os.path.dirname(schema_file)
        else:
            self.schema_path = None
        self.schema_file = schema_file

    def get_run_fn(self):
        return self.run_fn

    def run_fn(self):
        feature_spec = get_feature_spec_from_schema(self.schema_path)
        train_split_patterns = [self.input_patterns[split] for split in
                                self.split_mapping[utils.TRAIN_SPLITS]]
        train_dataset = self.input_fn(train_split_patterns,
                                      feature_spec)

        eval_split_patterns = [self.input_patterns[split] for split in
                               self.split_mapping[utils.EVAL_SPLITS]]
        eval_dataset = self.input_fn(eval_split_patterns,
                                     feature_spec)

        model = self.model_fn(train_dataset=train_dataset,
                              eval_dataset=eval_dataset)

        model.save_pretrained(self.serving_model_dir, saved_model=True)

    def model_fn(self,
                 train_dataset: tf.data.Dataset,
                 eval_dataset: tf.data.Dataset):

        id2label = {0: "FAKE_NEWS", 1: "REAL_NEWS"}

        model = TFDistilBertForSequenceClassification.from_pretrained(
            self.model_name, id2label=id2label)

        optimizer = tf.keras.optimizers.Adam(learning_rate=self.learning_rate)

        model.compile(optimizer=optimizer,
                      loss=model.compute_loss,
                      metrics=["accuracy"])

        model.fit(train_dataset,
                  epochs=self.epochs,
                  callbacks=[
                      tf.keras.callbacks.TensorBoard(
                          log_dir=os.path.join(self.log_dir, 'train'))])

        return model

    def input_fn(self,
                 file_pattern: List[Text],
                 feature_spec: Dict):
        """
        Feedforward input_fn for loading data from TFRecords saved to a
        location on disk.

        Args:
            file_pattern: File pattern matching saved TFRecords on disk.
            feature_spec: Feature spec from the inferred schema.

        Returns:
            dataset: tf.data.Dataset created out of the input files.
        """

        # grab BERT features plus the label
        bert_features = ["input_ids", "attention_mask"] + ["label"]

        feature_spec = {x: feature_spec[x]
                        for x in feature_spec
                        if x in bert_features}

        dataset = tf.data.experimental.make_batched_features_dataset(
            file_pattern=file_pattern,
            batch_size=self.batch_size,
            features=feature_spec,
            label_key="label",
            reader=self._gzip_reader_fn,
            num_epochs=1)

        return dataset

    @staticmethod
    def _gzip_reader_fn(filenames):
        """
        Small utility returning a record reader that can read gzipped files.

        Args:
            filenames: Names of the compressed TFRecord data files.
        """
        return tf.data.TFRecordDataset(filenames, compression_type='GZIP')

    def load_model(self, path_to_model: Text):
        return TFDistilBertForSequenceClassification.from_pretrained(
            path_to_model)
