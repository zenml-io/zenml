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

import tensorflow as tf
import tensorflow_transform as tft
from typing import Text, List, Any
from zenml.utils import path_utils
from zenml.core.steps.trainer.base_trainer import BaseTrainerStep

import tokenizers
import tokenizers.models
import tokenizers.implementations
from tokenizers.implementations import BertWordPieceTokenizer

# except ImportError:
#     print("Error: Library \"tokenizers\" not installed.")


class HFTokenizerStep(BaseTrainerStep):

    def __init__(self,
                 vocab_size: int,
                 min_frequency: int,
                 model: tokenizers.models.Model = None,
                 tokenizer: tokenizers.implementations.BaseTokenizer = None,
                 special_tokens: List[Text] = None,
                 train_files: Any = None,
                 eval_files: Any = None,
                 batch_size: int = 1024,
                 **kwargs):

        super(HFTokenizerStep, self).__init__(train_files=train_files,
                                              eval_files=eval_files,
                                              vocab_size=vocab_size,
                                              min_frequency=min_frequency,
                                              model=model,
                                              tokenizer=tokenizer,
                                              special_tokens=special_tokens,
                                              batch_size=batch_size,
                                              **kwargs)

        self.model = model
        self.batch_size = batch_size

        # for predefined tokenizer implementations from HuggingFace
        # if tokenizer is not None:
        #     self.tokenizer = tokenizer
        # else:
        # for customized tokenizers
        self.tokenizer = BertWordPieceTokenizer()
        self.vocab_size = vocab_size
        self.min_frequency = min_frequency
        self.special_tokens = special_tokens or []

    @staticmethod
    def _gzip_reader_fn(filenames):
        """
        Small utility returning a record reader that can read gzipped files.

        Args:
            filenames: Names of the compressed TFRecord data files.
        """
        return tf.data.TFRecordDataset(filenames, compression_type='GZIP')

    def input_fn(self,
                 file_pattern: List[Text],
                 tf_transform_output: tft.TFTransformOutput = None):

        features = {"category": tf.io.FixedLenFeature([], tf.int64),
                    "label": tf.io.FixedLenFeature([], tf.int64),
                    "news": tf.io.FixedLenFeature([], tf.string)}

        dataset = tf.data.experimental.make_batched_features_dataset(
            file_pattern=file_pattern,
            batch_size=self.batch_size,
            features=features,
            reader=self._gzip_reader_fn,
            num_epochs=1)

        return dataset

    def model_fn(self,
                 train_dataset: tf.data.Dataset,
                 eval_dataset: tf.data.Dataset):

        train_dataset = train_dataset.as_numpy_iterator()

        news_in_memory = list(train_dataset)[0]["news"]

        for i, n in enumerate(news_in_memory):
            news_in_memory[i] = n.decode("utf-8")

        self.tokenizer.train_from_iterator(news_in_memory)

        return self.tokenizer

    def run_fn(self):
        train_dataset = self.input_fn(self.train_files)
        eval_dataset = self.input_fn(self.eval_files)

        tokenizer = self.model_fn(train_dataset=train_dataset,
                                  eval_dataset=eval_dataset)

        path_utils.create_dir_if_not_exists(self.serving_model_dir)

        tokenizer.save_model(self.serving_model_dir)

