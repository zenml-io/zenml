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

import tensorflow as tf

import tensorflow_transform as tft


def _impute(tensor, replacement):
    """
    Args:
        tensor:
        replacement:
    """
    if isinstance(tensor, tf.sparse.SparseTensor):
        sparse = tf.sparse.SparseTensor(tensor.indices,
                                        tensor.values,
                                        [tensor.dense_shape[0], 1])
        return tf.sparse.to_dense(sp_input=sparse, default_value=replacement)
    else:
        return tensor


def custom_f(custom_value):
    """
    Args:
        custom_value:
    """

    def apply(x):
        x = _impute(x, custom_value)
        return x

    return apply


def min_f():
    def apply(x):
        m = tft.min(x)
        x = _impute(x, m)
        return x

    return apply


def max_f():
    def apply(x):
        m = tft.max(x)
        x = _impute(x, m)
        return x

    return apply


def mean_f():
    def apply(x):
        m = tft.mean(x)

        x = tf.cast(x, dtype=tf.float32)
        x = _impute(x, m)
        return x

    return apply
