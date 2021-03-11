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
"""Split step utils tests."""

import pytest
import tensorflow as tf

from zenml.steps.split.utils import get_categorical_value, \
    partition_cat_list


def test_get_categorical_value():

    feature = {"int64cat_col":
               tf.train.Feature(int64_list=tf.train.Int64List(value=[1])),
               "floatcat_col":
               tf.train.Feature(float_list=tf.train.FloatList(value=[42.0])),
               "bytescat_col":
               tf.train.Feature(bytes_list=tf.train.BytesList(
                   value=[b"test_string"]))
               }

    tf_example = tf.train.Example(features=tf.train.Features(feature=feature))

    int_value = get_categorical_value(tf_example, cat_col="int64cat_col")
    float_value = get_categorical_value(tf_example, cat_col="floatcat_col")
    str_value = get_categorical_value(tf_example, cat_col="bytescat_col")

    # ensure type consistency
    assert isinstance(int_value, int)
    assert isinstance(float_value, float)
    assert isinstance(str_value, str)

    # tests for a categorical feature that is not in the data
    with pytest.raises(AssertionError):
        _ = get_categorical_value(tf_example, cat_col="testest")


def test_partition_cat_list():
    cat_list = [f"cat{i}" for i in range(10)]

    c_ratio = {"train": 0.5,
               "eval": 0.3,
               "test": 0.2}

    cat_dict = partition_cat_list(cat_list=cat_list, c_ratio=c_ratio)

    assert [len(li) for li in cat_dict.values()] == [5, 3, 2]

    # test: two categories, but three folds
    cat_list = [f"cat{i}" for i in range(2)]

    c_ratio = {"train": 0.33,
               "eval": 0.33,
               "test": 0.34}

    cat_dict = partition_cat_list(cat_list=cat_list, c_ratio=c_ratio)

    # expected: train and eval each get one, test empty
    assert [len(li) for li in cat_dict.values()] == [1, 0, 1]

    # test: three categories and three folds
    cat_list = [f"cat{i}" for i in range(3)]

    c_ratio = {"train": 0.33,
               "eval": 0.33,
               "test": 0.34}

    cat_dict = partition_cat_list(cat_list=cat_list, c_ratio=c_ratio)

    # expected: train, eval, test each get one
    assert [len(li) for li in cat_dict.values()] == [1, 1, 1]
