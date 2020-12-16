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

import json
import os

import tensorflow as tf
from zenml.utils.standard_formats import UDFStandard

from zenml.utils.component_utils import parse_methods, get_bq_schema
from zenml.utils.component_utils import timer
from zenml.utils.constants import ZENML_PIPELINE_CONFIG
from zenml.utils.standards.standard_config import TransformMethods, \
    GlobalKeys, PreProcessKeys, PCAKeys, NonSeqFillingMethods, MethodKeys

PCA_PREFIX = 'pca_'


def apply_filling(data, description):
    """
    Args:
        data:
        description:
    """
    method_name = description[MethodKeys.METHOD]
    method_params = description[MethodKeys.PARAMETERS]
    return NonSeqFillingMethods.get_method(method_name)(**method_params)(data)


@timer
def preprocessing_fn(inputs):
    """
    Args:
        inputs:
    """
    config = json.loads(os.getenv(ZENML_PIPELINE_CONFIG))

    pca_config = config[GlobalKeys.PCA_]
    PCAKeys.key_check(pca_config)

    num_dims = pca_config[PCAKeys.NUM_DIMENSIONS]
    bq_schema = get_bq_schema(
        config[GlobalKeys.BQ_ARGS_],
        experiment_dict=config,
    )

    filling_dict = dict()
    for key in [GlobalKeys.FEATURES]:
        filling_dict.update(parse_methods(config[key],
                                          config[GlobalKeys.PREPROCESSING],
                                          PreProcessKeys.FILLING,
                                          bq_schema,
                                          NonSeqFillingMethods))

    # calculate normalized features
    norm_vecs = []
    pca_output = {}
    for key, value in inputs.items():
        if key in config[GlobalKeys.FEATURES] and bq_schema[key] != 'STRING':
            # TODO: [High] Add a way of imputing missing values
            value = apply_filling(value, filling_dict[key])

            # normalize to z score
            normed = TransformMethods.get_method('scale_to_z_score')(value)

            # cast of float32
            floated = tf.cast(normed, dtype=tf.float32)
            norm_vecs.append(floated)
        pca_output[key] = value  # also store the raw feature

    # concatenate all the norm features and calculate eigenvectors
    # multiply eigenvector matrix by features to get reduced features
    feature_matrix = tf.concat(norm_vecs, axis=1)
    pca = TransformMethods.get_method('pca')(feature_matrix,
                                             output_dim=num_dims,
                                             dtype=tf.float32)
    pca_features = tf.linalg.matmul(feature_matrix, pca)
    pca_features = tf.unstack(pca_features, axis=1)
    for i, f in enumerate(pca_features):
        pca_output[UDFStandard.ANALYZE_PREFIX + PCA_PREFIX + str(i)] = f

    return pca_output
