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

from typing import Any, Dict, List, Text

import os
import apache_beam as beam
import tensorflow as tf
from tfx import types
from tfx.dsl.components.base import base_executor
from tfx.types import artifact_utils
from zenml.core.standards.standard_keys import StepKeys
from zenml.core.steps.trainer.nlp_tokenizers.hf_tokenizer import \
    TokenizerStep
from zenml.core.components.split_gen.executor import WriteSplit
from zenml.utils import source_utils
from zenml.core.steps.split.utils import get_categorical_value
from zenml.utils import path_utils
from tfx.types.artifact_utils import get_split_uri
from tfx.utils import io_utils


def encode_sentence(ex: tf.train.Example, tokenizer: Any, text_feature: Text):
    sentence = get_categorical_value(ex, text_feature)

    encoded = tokenizer.encode(sentence)

    id_list = tf.train.Feature(
        int64_list=tf.train.Int64List(value=encoded.ids))
    token_list = tf.train.Feature(
        bytes_list=tf.train.BytesList(value=[
            tf.compat.as_bytes(" ".join(encoded.tokens))]))
    attention_list = tf.train.Feature(
        int64_list=tf.train.Int64List(value=encoded.attention_mask))

    new_feature = {"input_ids": id_list,
                   "tokens": token_list,
                   "attention_mask": attention_list}

    new_feature.update({
        f: ex.features.feature[f] for f in ex.features.feature
    })

    return tf.train.Example(features=tf.train.Features(feature=new_feature))


class TokenizerExecutor(base_executor.BaseExecutor):
    """
    Tokenizer executor. This component loads a previously trained
    tokenizer and uses it to transform the input data.
    """

    def Do(self, input_dict: Dict[Text, List[types.Artifact]],
           output_dict: Dict[Text, List[types.Artifact]],
           exec_properties: Dict[Text, Any]) -> None:

        source = exec_properties[StepKeys.SOURCE]
        args = exec_properties[StepKeys.ARGS]

        c = source_utils.load_source_path_class(source)
        tokenizer_step: TokenizerStep = c(**args)

        tokenizer_location = artifact_utils.get_single_uri(
            output_dict["tokenizer"])

        split_uris, split_names = [], []
        for artifact in input_dict["examples"]:
            for split in artifact_utils.decode_split_names(
                    artifact.split_names):
                split_names.append(split)
                uri = os.path.join(artifact.uri, split)
                split_uris.append((split, uri))

        # Get output split path
        output_examples = artifact_utils.get_single_instance(
            output_dict["output_examples"])
        output_examples.split_names = artifact_utils.encode_split_names(
            split_names)

        text_cache = artifact_utils.get_single_instance(
            output_dict["text_cache"])

        text_feature = tokenizer_step.text_feature

        with self._make_beam_pipeline() as p:
            # The outer loop will for now only run once
            for split, uri in split_uris:
                input_uri = io_utils.all_files_pattern(uri)
                output_uri = os.path.join(
                    text_cache.uri, "sentences_{}".format(split))

                # write text feature to files
                _ = (p
                     | 'ReadData.' + split >> beam.io.ReadFromTFRecord(
                            file_pattern=input_uri)
                     | "ParseTFExFromString." + split >> beam.Map(
                            tf.train.Example.FromString)
                     | "ExtractTextFeature." + split >> beam.Map(
                            get_categorical_value, cat_col=text_feature)
                     | "WriteToTextCache." + split >> beam.io.WriteToText(
                            output_uri,
                            file_name_suffix=".txt"))

        # get the previously created text files
        text_files = path_utils.list_dir(text_cache.uri)

        tokenizer_step.train(files=text_files)

        tokenizer_step.save(output_dir=tokenizer_location)

        # make a second pipeline for now
        with self._make_beam_pipeline() as p:
            for split, uri in split_uris:
                input_uri = io_utils.all_files_pattern(uri)

                _ = (p
                     | 'ReadData2.' + split >> beam.io.ReadFromTFRecord(
                        file_pattern=input_uri)
                     | "ParseTFExFromString2." + split >> beam.Map(
                            tf.train.Example.FromString)
                     | "AddTokens." + split >> beam.Map(
                            encode_sentence,
                            tokenizer=tokenizer_step.tokenizer,
                            text_feature=tokenizer_step.text_feature)
                     | 'Serialize2.' + split >> beam.Map(
                            lambda x: x.SerializeToString())
                     | 'WriteSplit2_' + split >> WriteSplit(
                            get_split_uri(
                                output_dict["output_examples"],
                                split)))
