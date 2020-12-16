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

from zenml.core.standards.standard_keys import MethodKeys
from zenml.core.steps.preprocesser.standard_preprocesser.methods import \
    methods_nonseq_filling, methods_transform


def parse_methods(input_dict, process, methods):
    """
    Args:
        input_dict:
        process:
        methods:
    """
    result = {}

    # Obtain the set of features
    f_set = set(input_dict.keys())
    f_list = list(sorted(f_set))

    for feature in f_list:
        assert isinstance(input_dict[feature], dict), \
            'Please specify a dict for every feature (empty dict if default)'

        # Check if the process for the given feature has been modified
        if process in input_dict[feature].keys():
            result[feature] = []
            for m in input_dict[feature][process]:
                MethodKeys.key_check(m)
                method_name = m[MethodKeys.METHOD]
                parameters = m[MethodKeys.PARAMETERS]
                # Check if the selected method exists and whether the
                # right parameters are given
                methods.check_name_and_params(method_name, parameters)
                result[feature].append(m)

    return result


class MethodDescriptions:
    MODES = {}

    @classmethod
    def check_name_and_params(cls, method_name, method_params):
        """
        Args:
            method_name:
            method_params:
        """
        assert method_name in cls.MODES.keys(), \
            'Choose one of the defined methods: {}'.format(cls.MODES.keys())

        assert all(
            p in method_params.keys() for p in cls.MODES[method_name][1]), \
            'All the required params {} of the {} needs to be defined' \
                .format(cls.MODES[method_name][1], method_name)

    @classmethod
    def get_method(cls, method_name):
        """
        Args:
            method_name:
        """
        return cls.MODES[method_name][0]


class NonSeqFillingMethods(MethodDescriptions):
    MODES = {'min': (methods_nonseq_filling.min_f, []),
             'max': (methods_nonseq_filling.max_f, []),
             'mean': (methods_nonseq_filling.mean_f, []),
             'custom': (methods_nonseq_filling.custom_f, ['custom_value'])}


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
             'image_reshape': (methods_transform.decode_and_reshape_image, []),
             'load_binary_image': (methods_transform.load_binary_image,
                                   []),
             'one_hot_encode': (methods_transform.one_hot_encode, ['depth'])}
