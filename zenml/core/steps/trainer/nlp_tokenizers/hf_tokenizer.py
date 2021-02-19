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
except ImportError:
    print("Error: Tokenizer library not installed.")


class HFTokenizerStep(BaseTrainerStep):

    def __init__(self,
                 output_dir: Text,
                 model: tokenizers.models.Model,
                 vocab_size: int,
                 min_frequency: int,
                 special_tokens: List[Text] = None,
                 train_files: Any = None,
                 eval_files: Any = None,
                 ):

        super(HFTokenizerStep, self).__init__(serving_model_dir=output_dir,
                                              train_files=train_files,
                                              eval_files=eval_files)

        self.model = model
        self.vocab_size = vocab_size
        self.min_frequency = min_frequency
        self.special_tokens = special_tokens or []

    def input_fn(self,
                 file_pattern: List[Text],
                 tf_transform_output: tft.TFTransformOutput):

        return tf.data.TFRecordDataset(filenames=file_pattern,
                                       compression_type="GZIP")


