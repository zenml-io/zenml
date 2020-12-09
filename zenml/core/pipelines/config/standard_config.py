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

import tensorflow_transform as tft

from zenml.core.components.session_transform.methods import \
    methods_resampling, \
    methods_label_tuning, methods_filling
from zenml.core.components.transform.methods import methods_nonseq_filling, \
    methods_transform
from zenml.core.pipelines.config.config_utils import ConfigKeys, \
    MethodDescriptions


class GlobalKeys(ConfigKeys):
    SPLIT = 'split'
    FEATURES = 'features'
    LABELS = 'labels'
    TRAINER = 'trainer'
    EVALUATOR = 'evaluator'
    PREPROCESSING = 'preprocessing'
    TIMESERIES_ = 'timeseries'
    PCA_ = 'pca'
    CUSTOM_CODE_ = 'custom_code'

    # following keys are MANUALLY added to the config during pipeline creation
    VERSION = 'version'
    BQ_ARGS_ = 'bq_args'


class DataSourceKeys(ConfigKeys):
    DATA_TYPE = 'type'
    DATA_SOURCE = 'source'
    ARGS = 'args'


class BQArgsKeys(ConfigKeys):
    PROJECT = 'project'
    DATASET = 'dataset'
    TABLE = 'table'


class GCSKeys(ConfigKeys):
    PATH = 'path'
    SERVICE_ACCOUNT = 'service_account'


class TimeSeriesKeys:
    RESAMPLING_RATE_IN_SECS = 'resampling_rate_in_secs'
    TRIP_GAP_THRESHOLD_IN_SECS = 'trip_gap_threshold_in_secs'

    PROCESS_SEQUENCE_W_TIMESTAMP = 'process_sequence_w_timestamp'
    PROCESS_SEQUENCE_W_CATEGORY_ = 'process_sequence_w_category'

    SEQUENCE_SHIFT = 'sequence_shift'
    SEQUENCE_LENGTH = 'sequence_length'


class SplitKeys(ConfigKeys):
    RATIO_ = "ratio"
    CATEGORIZE_BY_ = 'categorize'
    INDEX_BY_ = 'index'
    WHERE_ = 'where'


class EvaluatorKeys(ConfigKeys):
    SLICES_ = 'slices'
    METRICS_ = 'metrics'


class PCAKeys(ConfigKeys):
    NUM_DIMENSIONS = 'num_dimensions'


class TrainerKeys(ConfigKeys):
    FN = 'fn'
    PARAMS = 'params'


class DefaultKeys(ConfigKeys):
    STRING = 'string'
    INTEGER = 'integer'
    BOOLEAN = 'boolean'
    FLOAT = 'float'


class PreProcessKeys(ConfigKeys):
    RESAMPLING = 'resampling'
    FILLING = 'filling'
    TRANSFORM = 'transform'
    LABEL_TUNING = 'label_tuning'


class CustomCodeKeys(ConfigKeys):
    TRANSFORM_ = 'transform'
    MODEL_ = 'model'


class CustomCodeMetadataKeys(ConfigKeys):
    NAME = 'name'
    UDF_PATH = 'udf_path'
    STORAGE_PATH = 'storage_path'


class MethodKeys(ConfigKeys):
    METHOD = 'method'
    PARAMETERS = 'parameters'


#########################

class ResamplingMethods(MethodDescriptions):
    MODES = {'mean': (methods_resampling.resample_mean, []),
             'threshold': (methods_resampling.resample_thresholding,
                           ['cond', 'c_value', 'threshold', 'set_value']),
             'mode': (methods_resampling.resample_mode, []),
             'median': (methods_resampling.resample_median, [])}


class FillingMethods(MethodDescriptions):
    MODES = {'forward': (methods_filling.forward_f, []),
             'backwards': (methods_filling.backwards_f, []),
             'min': (methods_filling.min_f, []),
             'max': (methods_filling.max_f, []),
             'mean': (methods_filling.mean_f, []),
             'custom': (methods_filling.custom_f, ['custom_value'])}


class LabelTuningMethods(MethodDescriptions):
    MODES = {'leadup': (methods_label_tuning.tune_leadup,
                        ['event_value', 'duration']),
             'followup': (methods_label_tuning.tune_followup,
                          ['event_value', 'duration']),
             'shift': (methods_label_tuning.tune_shift,
                       ['shift_steps', 'fill_value']),
             'map': (methods_label_tuning.tune_map, ['mapper']),
             'no_tuning': (methods_label_tuning.no_tune, [])}


class TransformMethods(MethodDescriptions):
    MODES = {'scale_by_min_max': (tft.scale_by_min_max, ['min', 'max']),
             'scale_to_0_1': (tft.scale_to_0_1, []),
             'scale_to_z_score': (tft.scale_to_z_score, []),
             'tfidf': (tft.tfidf, ['vocab_size']),
             'compute_and_apply_vocabulary': (
                 tft.compute_and_apply_vocabulary, []),
             'ngrams': (tft.ngrams, ['ngram_range', 'separator']),
             'hash_strings': (tft.hash_strings, ['hash_buckets']),
             'pca': (tft.pca, ['output_dim', 'dtype']),
             'bucketize': (tft.bucketize, ['num_buckets']),
             'no_transform': (lambda x: x, []),
             'image_reshape': (methods_transform.image_reshape, ['height',
                                                                 'width',
                                                                 'num_channels'
                                                                 ]),
             'load_binary_image': (methods_transform.load_binary_image,
                                   []),
             'one_hot_encode': (methods_transform.one_hot_encode, ['depth'])}


class NonSeqFillingMethods(MethodDescriptions):
    MODES = {'min': (methods_nonseq_filling.min_f, []),
             'max': (methods_nonseq_filling.max_f, []),
             'mean': (methods_nonseq_filling.mean_f, []),
             'custom': (methods_nonseq_filling.custom_f, ['custom_value'])}


# class TrainerMethods(MethodDescriptions):
#     MODES = {'feedforward': (methods_trainer.feedforward, [])}
