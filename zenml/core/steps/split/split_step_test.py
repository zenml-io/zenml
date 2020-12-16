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
"""Tests for different split steps."""

import pytest
import tensorflow as tf
import random
from zenml.core.steps.split.categorical_domain_split_step import \
    CategoricalDomainSplitStep
from zenml.core.steps.split.categorical_ratio_split_step import \
    CategoricalRatioSplitStep
from zenml.core.steps.split.no_split_step import NoSplitStep
from zenml.core.steps.split.random_split import RandomSplitStep


@pytest.fixture
def create_random_dummy_data():

    def create_data():
        cat_col = "my_cat_col"
        possible_values = ["value{}".format(i+1) for i in range(3)]
        dummy_data = []

        for i in range(10):
            value = random.choice(possible_values).encode()
            feature = {cat_col: tf.train.Feature(
                bytes_list=tf.train.BytesList(value=[value]))}

            dummy_data.append(tf.train.Example(
                features=tf.train.Features(feature=feature)))

        return dummy_data

    return create_data


@pytest.fixture
def create_structured_dummy_data():

    def create_data(counts):

        cat_col = "my_cat_col"
        possible_values = ["value{}".format(i+1) for i in range(len(counts))]
        dummy_data = []

        for i, nums in enumerate(counts):
            value = possible_values[i].encode()
            feature = {cat_col: tf.train.Feature(
                bytes_list=tf.train.BytesList(value=[value]))}
            for n in range(nums):
                dummy_data.append(tf.train.Example(
                    features=tf.train.Features(feature=feature)))

        return dummy_data

    return create_data


def test_no_split(create_random_dummy_data):
    nosplit = NoSplitStep()
    nosplit_func = nosplit.partition_fn()[0]

    # test defaults
    assert not nosplit.schema
    assert not nosplit.statistics

    dummy_data = create_random_dummy_data()

    split_folds = [nosplit_func(ex, 1) for ex in dummy_data]

    # assert nosplit returns only one index
    assert all(fold == 0 for fold in split_folds)


def test_random_split(create_random_dummy_data):

    no_train = {"test": 0.5,
                "eval": 0.5}

    # no train argument present in split map
    with pytest.raises(AssertionError):
        _ = RandomSplitStep(split_map=no_train)

    one_fold = {"train": 1.0}

    # only one argument present in split map
    with pytest.raises(AssertionError):
        _ = RandomSplitStep(split_map=one_fold)

    bogus_entries = {"train": 0.5,
                     "eval": "testest"}

    # only one argument present in split map
    with pytest.raises(AssertionError):
        _ = RandomSplitStep(split_map=bogus_entries)

    split_map = {"train": 1.0,
                 "eval": 0.0}

    random_split = RandomSplitStep(split_map=split_map)
    random_split_func = random_split.partition_fn()[0]

    # test defaults
    assert not random_split.schema
    assert not random_split.statistics

    dummy_data = create_random_dummy_data()

    split_folds = [random_split_func(ex, 2, split_map=split_map)
                   for ex in dummy_data]

    # artificial no split result tests, everything else is random
    assert all(fold == 0 for fold in split_folds)


def test_categorical_domain_split(create_structured_dummy_data):

    cat_col = "my_cat_col"

    no_train = {"test": [],
                "eval": []}

    # no train argument present in split map
    with pytest.raises(AssertionError):
        _ = CategoricalDomainSplitStep(categorical_column=cat_col,
                                       split_map=no_train)

    one_fold = {"train": []}

    # only one argument present in split map
    with pytest.raises(AssertionError):
        _ = CategoricalDomainSplitStep(categorical_column=cat_col,
                                       split_map=one_fold)

    # real logic begins here
    split_map = {"train": ["value1"],
                 "eval": ["value2"],
                 "test": ["value3"]}

    domain_split = CategoricalDomainSplitStep(categorical_column=cat_col,
                                              split_map=split_map)

    # test defaults
    assert not domain_split.schema
    assert not domain_split.statistics

    domain_split_func = domain_split.partition_fn()[0]

    # each categorical value in the split map above gets one example
    counts = [1, 1, 1]

    dummy_data = create_structured_dummy_data(counts)

    split_folds = [domain_split_func(ex, 3,
                                     categorical_column=cat_col,
                                     split_map=split_map)
                   for ex in dummy_data]

    # fold indices, zero-based, should correspond to their dict counterparts
    assert split_folds == [0, 1, 2]

    # each categorical value in the split map above gets one example,
    # plus one out-of-split-map (unseen example)
    counts = [1, 1, 1, 1]

    dummy_data = create_structured_dummy_data(counts)

    split_folds = [domain_split_func(ex, 3,
                                     categorical_column=cat_col,
                                     split_map=split_map)
                   for ex in dummy_data]

    # default behavior is assigning everything into eval (index 1)
    assert split_folds == [0, 1, 2, 1]


def test_categorical_ratio_split(create_structured_dummy_data):

    cat_col = "my_cat_col"

    no_train = {"test": 0.5,
                "eval": 0.5}

    categories = []

    # no train argument present in split map
    with pytest.raises(AssertionError):
        _ = CategoricalRatioSplitStep(categorical_column=cat_col,
                                      categories=categories,
                                      split_ratio=no_train)

    one_fold = {"train": 1.0}

    # only one argument present in split map
    with pytest.raises(AssertionError):
        _ = CategoricalRatioSplitStep(categorical_column=cat_col,
                                      categories=categories,
                                      split_ratio=one_fold)

    # real logic begins here

    categories = ["value{}".format(i + 1) for i in range(3)]

    split_ratio = {"train": 0.33,
                   "eval": 0.33,
                   "test": 0.34}

    ratio_split = CategoricalRatioSplitStep(categorical_column=cat_col,
                                            categories=categories,
                                            split_ratio=split_ratio)

    # test defaults
    assert not ratio_split.schema
    assert not ratio_split.statistics

    ratio_split_func, args = ratio_split.partition_fn()

    split_map = args["split_map"]

    # each categorical value in the split map above gets one example
    counts = [1, 1, 1]

    dummy_data = create_structured_dummy_data(counts)

    split_folds = [ratio_split_func(ex, 3,
                                    categorical_column=cat_col,
                                    split_map=split_map)
                   for ex in dummy_data]

    # fold indices, zero-based, should correspond to their dict counterparts
    assert split_folds == [0, 1, 2]

    # each categorical value in the split map above gets one example,
    # plus one out-of-split-map (unseen example)
    counts = [1, 1, 1, 1]

    dummy_data = create_structured_dummy_data(counts)

    split_folds = [ratio_split_func(ex, 3,
                                    categorical_column=cat_col,
                                    split_map=split_map)
                   for ex in dummy_data]

    # default behavior is assigning everything into eval (index 1)
    assert split_folds == [0, 1, 2, 1]
