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

from zenml.core.components.session_transform.methods import methods_filling
from zenml.core.components.session_transform.methods import methods_resampling
from zenml.core.components.transform.methods import methods_nonseq_filling
from zenml.core.components.transform.methods import methods_transform
from zenml.core.pipelines.config.config_utils import MethodDescriptions


class ResamplingMethods(MethodDescriptions):
    MODES = {'mean': (methods_resampling.resample_mean, []),
             'threshold': (methods_resampling.resample_thresholding,
                           ['cond', 'c_value', 'threshold', 'set_value']),
             'mode': (methods_resampling.resample_mode, []),
             'median': (methods_resampling.resample_median, [])}


class NonSeqFillingMethods(MethodDescriptions):
    MODES = {'min': (methods_nonseq_filling.min_f, []),
             'max': (methods_nonseq_filling.max_f, []),
             'mean': (methods_nonseq_filling.mean_f, []),
             'custom': (methods_nonseq_filling.custom_f, ['custom_value'])}


class FillingMethods(MethodDescriptions):
    MODES = {'forward': (methods_filling.forward_f, []),
             'backwards': (methods_filling.backwards_f, []),
             'min': (methods_filling.min_f, []),
             'max': (methods_filling.max_f, []),
             'mean': (methods_filling.mean_f, []),
             'custom': (methods_filling.custom_f, ['custom_value'])}


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
