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
from zenml.core.steps.trainer.base_trainer import BaseTrainerStep

try:
    import tokenizers
    from tokenizers import Tokenizer
except ImportError:
    print("Error: Library \"tokenizers\" not installed.")


class HFTokenizerStep(BaseTrainerStep):

    def __init__(self,
                 vocab_size: int,
                 min_frequency: int,
                 model: tokenizers.models.Model = None,
                 tokenizer: tokenizers.implementations.BaseTokenizer = None,
                 special_tokens: List[Text] = None,
                 train_files: Any = None,
                 eval_files: Any = None,
                 ):

        super(HFTokenizerStep, self).__init__(train_files=train_files,
                                              eval_files=eval_files)

        self.model = model

        # for predefined tokenizer implementations from HuggingFace
        if tokenizer is not None:
            self.tokenizer = tokenizer
        else:
            # for customized tokenizers
            self.tokenizer = Tokenizer(self.model)
        self.vocab_size = vocab_size
        self.min_frequency = min_frequency
        self.special_tokens = special_tokens or []

    def input_fn(self,
                 file_pattern: List[Text],
                 tf_transform_output: tft.TFTransformOutput = None):

        return tf.data.TFRecordDataset(filenames=file_pattern,
                                       compression_type="GZIP")

    def model_fn(self,
                 train_dataset: tf.data.Dataset,
                 eval_dataset: tf.data.Dataset):

        train_dataset = train_dataset.batch(1024).as_numpy_iterator()
        eval_dataset = eval_dataset.batch(1024).as_numpy_iterator()

        self.tokenizer.train_from_iterator(train_dataset, trainer=None)

        return self.tokenizer

    def run_fn(self):
        train_dataset = self.input_fn(self.train_files)
        eval_dataset = self.input_fn(self.eval_files)

        tokenizer = self.model_fn(train_dataset=train_dataset,
                                  eval_dataset=eval_dataset)

        tokenizer.save_model(self.serving_model_dir)

