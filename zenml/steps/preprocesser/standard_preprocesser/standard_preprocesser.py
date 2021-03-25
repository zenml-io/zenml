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

from typing import Dict, List, Text, Any

import tensorflow as tf

from zenml.standards.standard_keys import MethodKeys, DefaultKeys
from zenml.steps.preprocesser import BasePreprocesserStep
from zenml.steps.preprocesser.standard_preprocesser.methods.standard_methods \
    import NonSeqFillingMethods, TransformMethods
from zenml.utils import naming_utils
from zenml.utils.preprocessing_utils import parse_methods, DEFAULT_DICT


def infer_schema(schema):
    """
    Function to infer a schema from input data.
    Args:
        schema: Input dict mapping features to tf.Tensors.

    Returns:
        schema_dict: Dict mapping features to their respective data types.
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


class StandardPreprocesser(BasePreprocesserStep):
    """
    Standard Preprocessor step. This step can be used to apply a variety of
    standard preprocessing techniques from the field of Machine Learning,
    which are predefined in ZenML, to the data.
    """

    def __init__(self,
                 features: List[Text] = None,
                 labels: List[Text] = None,
                 overwrite: Dict[Text, Any] = None,
                 **unused_kwargs):
        """
        Standard preprocessing step for generic preprocessing. Preprocessing
        steps are inferred on a feature-by-feature basis from its data type,
        and different standard preprocessing methods are applied based on the
        data type of the feature.

        The overwrite argument can also be used to overwrite the data
        type-specific standard preprocessing functions and apply other
        functions instead, given that they are registered in the default
        preprocessing method dictionary defined at the top of this file.

        An entry in the `overwrite` dict could look like this: ::

            {feature_name:
                {"transform": [{"method": "scale_to_z_score",
                                           "parameters": {}}],
                 "filling": [{"method": "max", "parameters": {}}]
            }
        
        Args:
            features: List of data features to be preprocessed.
            labels: List of features in the data that are to be predicted.
            overwrite: Dict of dicts, mapping features to a list of
             custom preprocessing and filling methods to be used.
            **unused_kwargs: Additional unused keyword arguments. Their usage
             might change in the future.
        """
        super(StandardPreprocesser, self).__init__(features=features,
                                                   labels=labels,
                                                   overwrite=overwrite,
                                                   **unused_kwargs)

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
        """
        Standard preprocessing function.
        Args:
            inputs: Dict mapping features to their respective data.

        Returns:
            output: Dict mapping transformed features to their respective
             transformed data.

        """
        schema = infer_schema(inputs)

        output = {}
        for key, value in inputs.items():
            if key not in self.f_dict:
                self.f_dict[key] = self.f_d_dict[schema[key]]
            value = self.apply_filling(value, self.f_dict[key])

            if key in self.features or key in self.labels:
                if key not in self.t_dict:
                    self.t_dict[key] = self.t_d_dict[schema[key]]
                result = self.apply_transform(key, value, self.t_dict[key])
                result = tf.cast(result, dtype=tf.float32)

                if key in self.features:
                    output[naming_utils.transformed_feature_name(key)] = result
                if key in self.labels:
                    output[naming_utils.transformed_label_name(key)] = result

            output[key] = value

        return output

    @staticmethod
    def apply_transform(key, data, transform_list):
        """
        Apply a list of transformations to input data.
        Args:
            key: Key argument specific to vocabulary computation.
            data: Data to be input into the transform functions.
            transform_list: List of transforms to apply to the data.

        Returns:
            data: Transformed data after each of the transforms in
             transform_list have been applied.

        """
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
        """
        Apply a list of fillings to input data.
        Args:
            data: Data to be input into the transform functions.
            filling_list: List of fillings to apply to the data. As of now,
             only the first filling in the list will be applied.

        Returns:
            data: Imputed data after the first filling in filling_list
            has been applied.

        """
        method_name = filling_list[0][MethodKeys.METHOD]
        method_params = filling_list[0][MethodKeys.PARAMETERS]
        return NonSeqFillingMethods.get_method(method_name)(**method_params)(
            data)

    def get_preprocessing_fn(self):
        return self.preprocessing_fn
