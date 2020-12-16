#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
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

import yaml

from zenml.core.pipelines.config.standard_config import GlobalKeys, SplitKeys

TEMPLATE_CONFIG = {
    GlobalKeys.VERSION: 1,
    GlobalKeys.SPLIT: {
        SplitKeys.CATEGORIZE_BY_: {'by': 'a_categorical_column',
                                   'ratio': {'train': 0.7,
                                             'eval': 0.3}},

        SplitKeys.INDEX_BY_: {'by': 'a_sequential_column',
                              'ratio': {'train': 0.6,
                                        'eval': 0.4}},
        SplitKeys.WHERE_: ['some_feature < 3',
                           'other_feature = 2']},
    GlobalKeys.FEATURES: {'training_feature_0': {},
                          'training_feature_1': {},
                          'training_feature_2': {},
                          'training_feature_3': {},
                          'training_feature_4': {}},

    GlobalKeys.EVALUATOR: {'evaluation_feature_0': {},
                           'evaluation_feature_1': {}},

    GlobalKeys.LABELS: {'label_column': {'loss': 'binary_crossentropy',
                                         'metrics': ['accuracy']}},

    GlobalKeys.TRAINER: {'architecture': 'feedforward',
                         'eval_batch_size': 64,
                         'last_activation': 'sigmoid',
                         'layers': [{'type': 'dense', 'units': 128},
                                    {'type': 'dense', 'units': 128},
                                    {'type': 'dense', 'units': 64}],
                         'num_output_units': 1,
                         'optimizer': 'adam',
                         'save_checkpoints_steps': 200,
                         'train_batch_size': 64,
                         'train_steps': 2000,
                         'type': 'classification'},

    GlobalKeys.PREPROCESSING: {
        'boolean': {'filling': [{'method': 'max',
                                 'parameters': {}}],
                    'label_tuning': [{'method': 'no_tuning',
                                      'parameters': {}}],
                    'resampling': [{'method': 'threshold',
                                    'parameters': {'c_value': 0,
                                                   'cond': 'greater',
                                                   'set_value': 1,
                                                   'threshold': 0}}],
                    'transform': [{'method': 'no_transform',
                                   'parameters': {}}]},
        'float': {'filling': [{'method': 'max',
                               'parameters': {}}],
                  'label_tuning': [{'method': 'no_tuning',
                                    'parameters': {}}],
                  'resampling': [{'method': 'mean',
                                  'parameters': {}}],
                  'transform': [{'method': 'scale_to_z_score',
                                 'parameters': {}}]},
        'integer': {'filling': [{'method': 'max', 'parameters': {}}],
                    'label_tuning': [{'method': 'no_tuning',
                                      'parameters': {}}],
                    'resampling': [{'method': 'mean',
                                    'parameters': {}}],
                    'transform': [{'method': 'scale_to_z_score',
                                   'parameters': {}}]},
        'string': {'filling': [{'method': 'custom',
                                'parameters': {'custom_value': ''}}],
                   'label_tuning': [{'method': 'no_tuning',
                                     'parameters': {}}],
                   'resampling': [{'method': 'mode',
                                   'parameters': {}}],
                   'transform': [{'method': 'compute_and_apply_vocabulary',
                                  'parameters': {}}]}}}

REQUIRED = [
    (GlobalKeys.VERSION,
     """
# This is the version of the configuration YAML!
#
# for more info: https://docs.maiot.io/your-pipeline-your-ideas/config-yaml
"""),
    (GlobalKeys.SPLIT, """
# The key 'split' is utilized to configure the process of splitting the 
dataset 
# into a training and an eval dataset.
#
#   - categorize_by:    A dictionary containing the options for a 
categorical split
#   - index_by:         A dictionary containing the options for an 
index-based split
#   - ratio:            A dictionary specifying a common percentage-based 
splitting
#                       approach for both categorical and index-based splits 
(if given)
#   - where:            A list of strings, which defines additional conditions
#                       while querying the datasource
#
# for more info: https://docs.maiot.io/splitting
"""),
    (GlobalKeys.FEATURES, """
# The main key `features` is used to define which set of features will be used 
# during the training and it allows the users to modify the pre-processing 
# steps filling, transform (and possibly resampling in case of sequential 
# data) for each one of these features.
#
# Structurally, each key under features represents a selected feature. 
# Under each key, the user has the chance to determine a method for each 
# pre-processing step to use. If it is not explicitly defined, the behaviour 
# will be inferred from the defaults based on the data type.
#
# for more info: https://docs.maiot.io/preprocessing/feature-selection
"""),
    (GlobalKeys.LABELS, """
# The main key labels is used to determine which data column will be used 
# as the label during the training. The inner structure of this column is 
# quite similar to the block features, where the keys denote the data columns  
# which are selected and the values include the pre-processing configuration
#
# for more info: https://docs.maiot.io/preprocessing/feature-selection
"""),
    (GlobalKeys.EVALUATOR, """
# The main key evaluator determines which data columns will be used in the 
# evaluation of the trained model. Structurally, it shares the same 
# structure as the features block.
#
# for more info: https://docs.maiot.io/preprocessing/feature-selection
"""),
    (GlobalKeys.TRAINER, """
# The main key trainer is used to configure the model and the training 
# parameters.
#
#   - architecture:             string value which determines the architecture 
#                               of the model, possible values include 
#                               'feedforward' for feedforward networks, 
#                               'sequence' for LSTM networks and 'sequence_ae' 
#                               for sequence-to-sequence autoencoders
#   - type:                     string value which defines the type of the 
#                               problem at hand, possible selections include 
#                               'regression', 'classification', 'autoencoder'
#   - train_batch_size:         the batch size during the training
#   - eval_batch_size:          the batch size during the eval steps
#   - train_steps:              the number of batches which should be 
#                               processed through the training
#   - save_checkpoints_steps:   the number of training batches, which will 
#                               indicate the frequency of the validation steps
#   - optimizer:                the name of the selected optimizer for the 
#                               training
#   - last_activation:          the name of the last layer in the model
#   - num_output_units:         the number of output units in the last layer
#   - sequence_length:          the length of the sequence in one data point 
#                               (provided only on a sequential problem setting)
#   - layers:                   list of dictionaries, which hold the layer 
#                               configurations
#
# for more info: https://docs.maiot.io/training-1/set-up-your-model-for
-training
"""),
    (GlobalKeys.PREPROCESSING, """
# This is the default preprocess block!
# 
# for more info: https://docs.maiot.io/preprocessing/data-transformations
"""),
]

OPTIONAL = [
    (GlobalKeys.TIMESERIES_, """
# This block configures the preprocessing steps specific to time-series 
# datasets. 
#
#   - resampling_rate_in_secs:      defines the resampling rate in seconds 
#                                   and it will be used at the corresponding 
#                                   pre-precessing step
#   - trip_gap_threshold_in_secs:   defines a maximum threshold in seconds in 
#                                   order to split the dataset into trips. 
#                                   Sequential transformations will occur once 
#                                   the data is split into trips based on 
this value.
#   - process_sequence_w_timestamp: specifies which data column holds the 
#                                   timestamp.
#   - process_sequence_w_category:  is an optional value, which, if provided, 
#                                   will be used to split the data into 
#                                   categories before the sequential processes
#   - sequence_shift:               defines the shift (in datapoints) while 
#                                   extracting sequences from the dataset
#
# for more info: https://docs.maiot.io/preprocessing/sequential-datasets
""")
]


def generate_comment_block(block, description):
    """
    Args:
        block:
        description:
    """
    return """##{filler}##
# {title} #
##{filler}##
{description}
""".format(filler='#' * len(block),
           title=block.upper(),
           description=description)


def generate_config_block(block, config):
    """
    Args:
        block:
        config:
    """
    return yaml.dump({block: config[block]}, default_flow_style=False) + '\n'


def save_pretty_yaml(config, output_path, no_docs):
    """
    Args:
        config:
        output_path:
        no_docs:
    """
    with open(output_path, "w") as output_file:
        for block, description in REQUIRED:
            if not no_docs:
                comment = generate_comment_block(block, description)
                output_file.writelines(comment)
            block = generate_config_block(block, config)
            output_file.writelines(block)

        for block, description in OPTIONAL:
            if block in config:
                if not no_docs:
                    comment = generate_comment_block(block, description)
                    output_file.writelines(comment)
                block = generate_config_block(block, config)
                output_file.writelines(block)
