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
from typing import Dict, Union

import tensorflow as tf
import tokenizers
from tokenizers.implementations import BertWordPieceTokenizer

from zenml.core.repo.repo import Repository
from zenml.core.steps.preprocesser.base_preprocesser import \
    BasePreprocesserStep
from zenml.core.steps.preprocesser.standard_preprocesser \
    .standard_preprocesser import \
    transformed_name

MAX_LEN = 128


def get_tokenizer_dir():
    """Manual loading of latest tokenizer artifact because we cannot
    inject it into the transform just yet."""
    repo: Repository = Repository.get_instance()

    artifact_store = repo.get_default_artifact_store()
    tokenizer_base = os.path.join(artifact_store.path,
                                  artifact_store.unique_id,
                                  "tokenizer",
                                  "tokenizer")

    # artifact dirs are numbers, so max gets the highest (= newest)
    latest_tokenizer = max(next(os.walk(tokenizer_base))[1])

    return os.path.join(tokenizer_base, latest_tokenizer)


def tokenize_from_tensor(tensor: Union[tf.Tensor, tf.SparseTensor],
                         tokenizer: tokenizers.implementations.BaseTokenizer):
    dense = tf.sparse.to_dense(tensor)
    encoded_tokens = tokenizer.encode(tf.compat.as_str_any(dense)).tokens
    encoded_ids = tokenizer.encode(tf.compat.as_str_any(dense)).ids

    encoded_tokens = encoded_tokens[:, :MAX_LEN]
    encoded_ids = encoded_ids[:, :MAX_LEN]

    return encoded_tokens, encoded_ids


class UrduPreprocessor(BasePreprocesserStep):

    def __init__(self, **kwargs):
        super(UrduPreprocessor, self).__init__(**kwargs)

        try:
            self.vocab_file = os.path.join(get_tokenizer_dir(), "vocab.txt")
        except:
            self.vocab_file = None

        # self.tokenizer = BertWordPieceTokenizer(vocab=self.vocab_file)

    def preprocessing_fn(self, inputs: Dict):
        outputs = {}
        for k, v in inputs.items():
            outputs[transformed_name(k)] = v

        return outputs
