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


from typing import Dict, List, Text

import tensorflow as tf
import tensorflow_transform as tft

from zenml.steps.preprocesser import BasePreprocesserStep
from zenml.steps.preprocesser.standard_preprocesser.methods \
    .methods_nonseq_filling import \
    _impute
from zenml.utils import naming_utils


def decode_image(input_):
    densed = tf.sparse.to_dense(input_)
    image = tf.map_fn(lambda x: tf.io.decode_image(x[0], channels=3), densed,
                      dtype=tf.uint8)
    return image


def reshape_image(input_, shape):
    image = (tf.cast(input_, tf.float32) / 127.5) - 1
    image = tf.reshape(image, shape)
    return image


class ImagePreprocessor(BasePreprocesserStep):
    def __init__(self, shape: List = None, image_key: Text = 'image',
                 labels: List = None, **kwargs):
        if shape is None:
            shape = []
        if labels is None:
            labels = []
        self.shape = shape
        self.labels = labels
        self.image_key = image_key
        super().__init__(shape=shape, image_key=image_key, labels=labels,
                         **kwargs)

    def preprocessing_fn(self, inputs: Dict):

        outputs = {}

        for k, v in inputs.items():
            if k == self.image_key:
                result = decode_image(v)
                result = reshape_image(result, shape=self.shape)
                result = tf.cast(result, dtype=tf.float32)
                outputs[naming_utils.transformed_feature_name(k)] = result
            if k in self.labels:
                m = tft.max(v)
                result = _impute(v, m)
                # always retain raw data
                outputs[k] = result

                result = tf.cast(v, dtype=tf.float32)
                outputs[naming_utils.transformed_label_name(k)] = result


        return outputs
