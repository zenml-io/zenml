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

import tensorflow as tf

from zenml.steps.split.utils import get_categorical_value
from zenml.steps.tokenizer import BaseTokenizer
from zenml.steps.tokenizer.utils import tokenizer_map
from zenml.utils import path_utils


class HuggingFaceTokenizerStep(BaseTokenizer):
    """
    Base step for Tokenizer usage in NLP pipelines.

    This step can be used in Natural Language Processing (NLP) pipelines,
    where tokenization is a special form of preprocessing for text data in
    sequence form.

    This step was primarily designed to integrate the Huggingface ecosystem
    (transformers, tokenizers, datasets) into ZenML. Other tokenization
    libraries can work with this step, but are not guaranteed to work.
    """

    def __init__(self,
                 text_feature: Text,
                 tokenizer: Text,
                 tokenizer_params: Dict[Text, Any] = None,
                 skip_training: bool = False,
                 vocab_size: int = 30000,
                 min_frequency: int = 2,
                 sentence_length: int = 128,
                 special_tokens: List[Text] = None,
                 batch_size: int = 64,
                 **kwargs):
        """
        Tokenizer step constructor.

        Args:
            text_feature: String, name of the text feature in the data.
            tokenizer: String, name of the Huggingface tokenizer to use.
             Can be either one of "bert-wordpiece", "byte-level-bpe",
              "char-level-bpe", "sentencepiece-bpe", "sentencepiece-unigram".
            tokenizer_params: Keyword arguments to be used in construction of
             the tokenizer given by the tokenizer argument.
            skip_training: Boolean indicating whether or not to skip training
             the tokenizer in the pipeline.
            vocab_size: Size of the target vocabulary.
            min_frequency: Minimal frequency of an element to be included into
             the vocabulary.
            sentence_length: Sentence length. Varies depending on the target
             model, usually 128 for BERT-based models. Longer sentences will
             be padded, shorter sentences will be truncated to match length.
            special_tokens: List of special tokens to include.
            batch_size: Batch size to use when training the tokenizer from an
             iterator.
            **kwargs: Additional keyword arguments.
        """

        super(HuggingFaceTokenizerStep, self).__init__(
            text_feature=text_feature,
            skip_training=skip_training,
            vocab_size=vocab_size,
            min_frequency=min_frequency,
            sentence_length=sentence_length,
            tokenizer=tokenizer,
            tokenizer_params=tokenizer_params,
            special_tokens=special_tokens,
            batch_size=batch_size,
            **kwargs)

        # training arguments for tokenizer
        self.vocab_size = vocab_size
        self.min_frequency = min_frequency
        self.special_tokens = special_tokens or [
            "[PAD]",
            "[UNK]",
            "[CLS]",
            "[SEP]",
            "[MASK]",
        ]

        # tokenizer config sub-block
        self.tokenizer_name = tokenizer
        self.tokenizer_params = tokenizer_params or {}
        self.sentence_length = sentence_length
        self.batch_size = batch_size
        self.tokenizer = tokenizer_map.get(
            self.tokenizer_name)(**self.tokenizer_params)

        # truncation and padding constrain length to sentence_length
        self.tokenizer.enable_padding(length=self.sentence_length)
        self.tokenizer.enable_truncation(max_length=self.sentence_length)

    def train(self, files: List[Text]):
        """
        Method for training a tokenizer on a data iterator. The iterator is
        constructed inside the function in a closure from a TFRecord dataset.

        Args:
            files: List of TFRecord files in GZIP format to ingest.
        """
        ds = tf.data.TFRecordDataset(files, compression_type="GZIP")

        ds_numpy = ds.batch(self.batch_size).as_numpy_iterator()

        def build_scoped_iterator(text_feature):
            for batch in ds_numpy:
                yield [get_categorical_value(
                    tf.train.Example.FromString(ex),
                    text_feature) for ex in batch]

        iterator = build_scoped_iterator(self.text_feature)

        # showing progress does not work in logging mode apparently
        self.tokenizer.train_from_iterator(iterator=iterator,
                                           vocab_size=self.vocab_size,
                                           min_frequency=self.min_frequency,
                                           special_tokens=self.special_tokens,
                                           show_progress=False)

    def save(self, output_dir: Text):
        """
        Save a trained tokenizer model to disk.

        Args:
            output_dir: Path to which to save the trained tokenizer.
        """

        # save_model does not attempt to create the destination, so create it
        path_utils.create_dir_if_not_exists(output_dir)

        self.tokenizer.save_model(directory=output_dir)

    def load_vocab(self, path_to_vocab: Text):
        """
        Re-instantiate the class tokenizer with output vocabulary / merges.

        Args:
            path_to_vocab: Path to vocab / merges files from a training run.
        """

        # inspect contents of output dir
        contents = path_utils.list_dir(path_to_vocab)

        try:
            vocab_file = next(f for f in contents if "vocab" in f)
        except StopIteration:
            vocab_file = None

        # update tokenizer params with vocab file name
        self.tokenizer_params.update({"vocab": vocab_file})

        # merges are only needed for BPE Tokenizers
        if "bpe" in self.tokenizer_name:
            try:
                merges_file = next(f for f in contents if "merge" in f)
            except StopIteration:
                merges_file = None

            self.tokenizer_params.update({"merges": merges_file})

        # reconstruct tokenizer object
        self.tokenizer = tokenizer_map.get(
            self.tokenizer_name)(**self.tokenizer_params)
        self.tokenizer.enable_padding(length=self.sentence_length)
        self.tokenizer.enable_truncation(max_length=self.sentence_length)

    def encode(self, sequence: Text, output_format: Text = "tf_example"):
        """
        Encode a sentence with the tokenizer in this class and output it into
        the specified output format. Supported return types are "tf_tensors",
        returning a dictionary of tensorflow tensor objects, "dict", returning
        a dictionary of lists, and "tf_example", returning a tf.train.Example
        proto file.

        Args:
            sequence: String, sentence to encode with the trained tokenizer.
            output_format: String specifying output format. Can be either
             `tf_tensors`, `dict` or `tf_example`.

        Returns:
            A representation of the sentence in IDs based on the vocabulary
             of the tokenizer.
        """
        eligible_formats = ["tf_tensors", "dict", "tf_example"]

        if output_format not in eligible_formats:
            raise ValueError("Unrecognized format {0}. Output format must be "
                             "one of: {1}".format(output_format,
                                                  ", ".join(eligible_formats)
                                                  ))

        encoded = self.tokenizer.encode(sequence=sequence)

        if output_format == "tf_example":
            feature = {"input_ids": tf.train.Feature(
                int64_list=tf.train.Int64List(value=encoded.ids)),
                "attention_mask": tf.train.Feature(
                    int64_list=tf.train.Int64List(
                        value=encoded.attention_mask))}

            output = tf.train.Example(
                features=tf.train.Features(feature=feature))

        elif output_format == "dict":
            output = {"input_ids": encoded.ids,
                      "attention_mask": encoded.attention_mask}

        else:
            # output format is tf_tensors
            output = {"input_ids": tf.convert_to_tensor(encoded.ids,
                                                        dtype=tf.int32),
                      "attention_mask": tf.convert_to_tensor(
                          encoded.attention_mask,
                          dtype=tf.int32)}
        return output
