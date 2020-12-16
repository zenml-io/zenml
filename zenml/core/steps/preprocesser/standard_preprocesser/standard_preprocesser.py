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

from typing import Dict, List, Text, Any

import tensorflow as tf

from zenml.core.standards.standard_keys import MethodKeys, DefaultKeys
from zenml.core.steps.preprocesser.base_preprocesser import \
    BasePreprocesserStep
from zenml.core.steps.preprocesser.standard_preprocesser.methods \
    .standard_methods import NonSeqFillingMethods, TransformMethods, \
    parse_methods

XF_SUFFIX = '_xf'



DEFAULT_DICT = {
    'boolean': {
        'filling': [{'method': 'max', 'parameters': {}}],
        'resampling': [{'method': 'threshold',
                        'parameters': {'c_value': 0,
                                       'cond': 'greater',
                                       'set_value': 1,
                                       'threshold': 0}}],
        'transform': [{'method': 'no_transform', 'parameters': {}}]},
    'float': {
        'filling': [{'method': 'max', 'parameters': {}}],
        'resampling': [{'method': 'mean', 'parameters': {}}],
        'transform': [{'method': 'scale_to_z_score', 'parameters': {}}]},
    'integer': {
        'filling': [{'method': 'max', 'parameters': {}}],
        'resampling': [{'method': 'mean', 'parameters': {}}],
        'transform': [{'method': 'scale_to_z_score', 'parameters': {}}]},
    'string': {
        'filling': [{'method': 'custom', 'parameters': {'custom_value': ''}}],
        'resampling': [{'method': 'mode', 'parameters': {}}],
        'transform': [{'method': 'compute_and_apply_vocabulary',
                       'parameters': {}}]
    }}


def transformed_name(key):
    """
    Args:
        key:
    """
    return key + XF_SUFFIX


def infer_schema(schema):
    """
    Args:
        schema:
    """
    schema_dict = dict()
    for feature, descriptions in schema.items():
        dtype = descriptions.dtype
        # These are ugly hacks for hard checking whether its broadly int, float
        #  bool or string.
        if dtype == float or 'float' in str(dtype):
            schema_dict[feature] = DefaultKeys.FLOAT
        elif dtype == int or 'int' in str(dtype):
            schema_dict[feature] = DefaultKeys.INTEGER
        elif dtype == bool or 'bool' in str(dtype):
            schema_dict[feature] = DefaultKeys.BOOLEAN
        elif dtype == str or 'string' in str(dtype):
            schema_dict[feature] = DefaultKeys.STRING
        else:
            raise AssertionError('Cannot infer schema dtype!')
    return schema_dict


class StandardPreprocessor(BasePreprocesserStep):

    def __init__(self,
                 features: List[Text] = None,
                 labels: List[Text] = None,
                 overwrite: Dict[Text, Any] = None,
                 **unused_kwargs):
        """
        Standard preprocesser step for generic preprocessing.
        
        Args:
            features:
            labels:
            overwrite:
            **unused_kwargs:
        """
        super().__init__(features=features, labels=labels, overwrite=overwrite)

        # List of features and labels
        self.features = features or []
        self.labels = labels or []

        self.t_dict = parse_methods(overwrite or {},
                                    'transform',
                                    TransformMethods)

        self.t_d_dict = parse_methods(DEFAULT_DICT,
                                      'transform',
                                      TransformMethods)

        self.f_dict = parse_methods(overwrite or {},
                                    'filling',
                                    NonSeqFillingMethods)

        self.f_d_dict = parse_methods(DEFAULT_DICT,
                                      'filling',
                                      NonSeqFillingMethods)

    def preprocessing_fn(self, inputs: Dict):
        schema = infer_schema(inputs)

        output = {}
        for key, value in inputs.items():
            if key in self.features or key in self.labels:

                if key not in self.f_dict:
                    self.f_dict[key] = self.f_d_dict[schema[key]]
                value = self.apply_filling(value, self.f_dict[key])

                if key not in self.t_dict:
                    self.t_dict[key] = self.t_d_dict[schema[key]]
                result = self.apply_transform(key, value, self.t_dict[key])
                result = tf.cast(result, dtype=tf.float32)

                if key in self.features:
                    output[transformed_name(key)] = result

                if key in self.labels:
                    output[transformed_name('label_' + key)] = result

            output[key] = value

        return output

    @staticmethod
    def apply_transform(key, data, transform_list):
        for transform in transform_list:
            method_name = transform[MethodKeys.METHOD]
            method_params = transform[MethodKeys.PARAMETERS]

            if method_name == 'compute_and_apply_vocabulary':
                method_params.update({'vocab_filename': key})

            data = TransformMethods.get_method(method_name)(data,
                                                            **method_params)
        return data

    @staticmethod
    def apply_filling(data, filling_list):
        method_name = filling_list[0][MethodKeys.METHOD]
        method_params = filling_list[0][MethodKeys.PARAMETERS]
        return NonSeqFillingMethods.get_method(method_name)(**method_params)(
            data)

    def get_preprocessing_fn(self):
        return self.preprocessing_fn
