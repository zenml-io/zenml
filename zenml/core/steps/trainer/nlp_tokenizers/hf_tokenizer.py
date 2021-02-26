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

from typing import Text, List, Any
from zenml.utils import path_utils
from zenml.core.steps.base_step import BaseStep

import tokenizers.models
import tokenizers.implementations
from tokenizers.implementations import BertWordPieceTokenizer


class TokenizerStep(BaseStep):

    def __init__(self,
                 text_feature: Text,
                 vocab_size: int,
                 min_frequency: int,
                 model: tokenizers.models.Model = None,
                 tokenizer: tokenizers.implementations.BaseTokenizer = None,
                 special_tokens: List[Text] = None,
                 **kwargs):

        super(TokenizerStep, self).__init__(text_feature=text_feature,
                                            vocab_size=vocab_size,
                                            min_frequency=min_frequency,
                                            model=model,
                                            tokenizer=tokenizer,
                                            special_tokens=special_tokens,
                                            **kwargs)

        self.model = model
        self.text_feature = text_feature

        # for predefined tokenizer implementations from HuggingFace
        # if tokenizer is not None:
        #     self.tokenizer = tokenizer
        # else:
        # for customized tokenizers
        self.tokenizer = BertWordPieceTokenizer()
        self.tokenizer.enable_padding(length=128)
        self.tokenizer.enable_truncation(max_length=128)
        self.vocab_size = vocab_size
        self.min_frequency = min_frequency
        self.special_tokens = special_tokens or [
            "[PAD]",
            "[UNK]",
            "[CLS]",
            "[SEP]",
            "[MASK]",
        ]

    def train(self, files: List[Text]):
        self.tokenizer.train(files=files,
                             vocab_size=self.vocab_size,
                             min_frequency=self.min_frequency,
                             special_tokens=self.special_tokens)

    def save(self, output_dir: Text):
        path_utils.create_dir_if_not_exists(output_dir)

        self.tokenizer.save_model(directory=output_dir)
