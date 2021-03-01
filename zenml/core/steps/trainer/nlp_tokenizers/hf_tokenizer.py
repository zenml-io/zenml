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

from typing import Dict, Text, List, Any
from zenml.utils import path_utils
from zenml.core.steps.base_step import BaseStep
from zenml.core.steps.trainer.nlp_tokenizers.utils import tokenizer_map


class TokenizerStep(BaseStep):

    def __init__(self,
                 text_feature: Text,
                 tokenizer: Text,
                 tokenizer_params: Dict[Text, Any] = None,
                 vocab_size: int = 30000,
                 min_frequency: int = 2,
                 sentence_length: int = 128,
                 special_tokens: List[Text] = None,
                 **kwargs):

        super(TokenizerStep, self).__init__(text_feature=text_feature,
                                            vocab_size=vocab_size,
                                            min_frequency=min_frequency,
                                            sentence_length=sentence_length,
                                            tokenizer=tokenizer,
                                            tokenizer_params=tokenizer_params,
                                            special_tokens=special_tokens,
                                            **kwargs)

        self.text_feature = text_feature
        self.tokenizer_params = tokenizer_params or {}

        # for customized tokenizers
        self.tokenizer = tokenizer_map.get(tokenizer)(**self.tokenizer_params)

        # truncation and padding constrain length to sentence_length
        self.tokenizer.enable_padding(length=sentence_length)
        self.tokenizer.enable_truncation(max_length=sentence_length)
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
        # showing progress does not work in logging mode apparently
        self.tokenizer.train(files=files,
                             vocab_size=self.vocab_size,
                             min_frequency=self.min_frequency,
                             special_tokens=self.special_tokens,
                             show_progress=False)

    def save(self, output_dir: Text):
        path_utils.create_dir_if_not_exists(output_dir)

        self.tokenizer.save_model(directory=output_dir)
