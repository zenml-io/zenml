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
from typing import Any, Dict, List, Text

import apache_beam as beam
import tensorflow as tf
from tfx import types
from tfx.dsl.components.base import base_executor
from tfx.types import artifact_utils
from tfx.types.artifact_utils import get_split_uri
from tfx.utils import io_utils

from zenml.components.split_gen.executor import WriteSplit
from zenml.standards.standard_keys import StepKeys
from zenml.steps.split.utils import get_categorical_value
from zenml.steps.tokenizer import BaseTokenizer
from zenml.utils import path_utils, source_utils


def append_tf_example(ex: tf.train.Example, tokenizer_step: BaseTokenizer):
    """
    Append the tokenizer encoding outputs as features to the existing data
    in tf.train.Example format.

    Args:
        ex: tf.train.Example with the raw input features.
        tokenizer_step: Local tokenizer step used in the NLP pipeline.

    Returns:
        A tf.train.Example with all of the features from the `ex` input,
         plus two features `input_ids` and `attention_mask` holding the word
         IDs and attention mask outputs from the tokenizer.

    """
    sentence = get_categorical_value(ex, tokenizer_step.text_feature)

    encoded = tokenizer_step.encode(sentence, output_format="dict")

    new_feature = {k: tf.train.Feature(
        int64_list=tf.train.Int64List(value=v)) for k, v in encoded.items()}

    new_feature.update({
        f: ex.features.feature[f] for f in ex.features.feature
    })

    return tf.train.Example(features=tf.train.Features(feature=new_feature))


class TokenizerExecutor(base_executor.BaseExecutor):
    """
    Tokenizer executor. This component uses a tokenizer, either already
    trained or newly instantiated, and uses it to transform the input data.
    """

    def Do(self, input_dict: Dict[Text, List[types.Artifact]],
           output_dict: Dict[Text, List[types.Artifact]],
           exec_properties: Dict[Text, Any]) -> None:

        source = exec_properties[StepKeys.SOURCE]
        args = exec_properties[StepKeys.ARGS]

        c = source_utils.load_source_path_class(source)
        tokenizer_step: BaseTokenizer = c(**args)

        tokenizer_location = artifact_utils.get_single_uri(
            output_dict["tokenizer"])

        split_uris, split_names, all_files = [], [], []
        for artifact in input_dict["examples"]:
            for split in artifact_utils.decode_split_names(
                    artifact.split_names):
                split_names.append(split)
                uri = os.path.join(artifact.uri, split)
                split_uris.append((split, uri))
                all_files += path_utils.list_dir(uri)

        # Get output split path
        output_examples = artifact_utils.get_single_instance(
            output_dict["output_examples"])
        output_examples.split_names = artifact_utils.encode_split_names(
            split_names)

        if not tokenizer_step.skip_training:
            tokenizer_step.train(files=all_files)

            tokenizer_step.save(output_dir=tokenizer_location)

        with self._make_beam_pipeline() as p:
            for split, uri in split_uris:
                input_uri = io_utils.all_files_pattern(uri)

                _ = (p
                     | 'ReadData.' + split >> beam.io.ReadFromTFRecord(
                            file_pattern=input_uri)
                     | "ParseTFExFromString." + split >> beam.Map(
                            tf.train.Example.FromString)
                     | "AddTokens." + split >> beam.Map(
                            append_tf_example,
                            tokenizer_step=tokenizer_step)
                     | 'Serialize.' + split >> beam.Map(
                            lambda x: x.SerializeToString())
                     | 'WriteSplit.' + split >> WriteSplit(
                            get_split_uri(
                                output_dict["output_examples"],
                                split)))
