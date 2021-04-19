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

import random

import pytest
import tensorflow as tf

from zenml.steps.split import CategoricalDomainSplit
from zenml.steps.split import CategoricalRatioSplit
from zenml.steps.split import NoSplit
from zenml.steps.split import RandomSplit


@pytest.fixture
def create_random_dummy_data():
    def create_data():
        cat_col = "my_cat_col"
        possible_values = ["value{}".format(i + 1) for i in range(3)]
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
        possible_values = ["value{}".format(i + 1) for i in range(len(counts))]
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
    nosplit = NoSplit()

    # test defaults
    assert not nosplit.schema
    assert not nosplit.statistics

    dummy_data = create_random_dummy_data()

    split_folds = [nosplit.partition_fn(ex, nosplit.get_num_splits())
                   for ex in dummy_data]

    # assert nosplit returns only one index
    assert all(fold == 0 for fold in split_folds)


def test_random_split(create_random_dummy_data):
    one_fold = {"train": 1.0}

    # only one argument present in split map
    with pytest.raises(AssertionError):
        _ = RandomSplit(split_map=one_fold)

    bogus_entries = {"train": 0.5,
                     "eval": "testest"}

    # not all entries in split map are floats
    with pytest.raises(AssertionError):
        _ = RandomSplit(split_map=bogus_entries)

    split_map = {"train": 1.0,
                 "eval": 0.0}

    random_split = RandomSplit(split_map=split_map)

    # test defaults
    assert not random_split.schema
    assert not random_split.statistics

    dummy_data = create_random_dummy_data()

    split_folds = [random_split.partition_fn(ex, random_split.get_num_splits())
                   for ex in dummy_data]

    # artificial no split result tests, everything else is random
    assert all(fold == 0 for fold in split_folds)


def test_categorical_domain_split(create_structured_dummy_data):
    cat_col = "my_cat_col"

    one_fold = {"train": []}

    # only one argument present in split map
    with pytest.raises(AssertionError):
        _ = CategoricalDomainSplit(categorical_column=cat_col,
                                   split_map=one_fold)

    # real logic begins here
    split_map = {"train": ["value1"],
                 "eval": ["value2"],
                 "test": ["value3"]}

    domain_split = CategoricalDomainSplit(categorical_column=cat_col,
                                          split_map=split_map)

    # test defaults
    assert not domain_split.schema
    assert not domain_split.statistics

    # each categorical value in the split map above gets one example
    counts = [1, 1, 1]

    dummy_data = create_structured_dummy_data(counts)

    split_folds = [domain_split.partition_fn(ex, domain_split.get_num_splits())
                   for ex in dummy_data]

    # fold indices, zero-based, should correspond to their dict counterparts
    assert split_folds == [0, 1, 2]

    # each categorical value in the split map above gets one example,
    # plus one out-of-split-map (unseen example)
    counts = [1, 1, 1, 1]

    dummy_data = create_structured_dummy_data(counts)

    split_folds = [domain_split.partition_fn(ex, domain_split.get_num_splits())
                   for ex in dummy_data]

    assert domain_split.get_num_splits() == 4

    # default behavior is skipping (index n-1 = 3)
    assert split_folds == [0, 1, 2, 3]

    # test whether eval assignment works
    domain_split.unknown_category_policy = "eval"

    # each categorical value in the split map above gets one example,
    # plus one out-of-split-map (unseen example)
    counts = [1, 1, 1, 1]

    dummy_data = create_structured_dummy_data(counts)

    split_folds = [domain_split.partition_fn(ex, domain_split.get_num_splits())
                   for ex in dummy_data]

    assert domain_split.get_num_splits() == 3

    # default behavior is eval (index 1)
    assert split_folds == [0, 1, 2, 1]


def test_categorical_ratio_split(create_structured_dummy_data):
    cat_col = "my_cat_col"

    categories = []

    one_fold = {"train": 1.0}

    # only one fold present in split map
    with pytest.raises(AssertionError):
        _ = CategoricalRatioSplit(categorical_column=cat_col,
                                  categories=categories,
                                  split_ratio=one_fold)

    # real logic begins here
    categories = ["value{}".format(i + 1) for i in range(3)]

    split_ratio = {"train": 0.33,
                   "eval": 0.33,
                   "test": 0.34}

    ratio_split = CategoricalRatioSplit(categorical_column=cat_col,
                                        categories=categories,
                                        split_ratio=split_ratio)

    # test defaults
    assert not ratio_split.schema
    assert not ratio_split.statistics

    # each categorical value in the split map above gets one example
    counts = [1, 1, 1]

    dummy_data = create_structured_dummy_data(counts)

    split_folds = [ratio_split.partition_fn(ex, ratio_split.get_num_splits())
                   for ex in dummy_data]

    # fold indices, zero-based, should correspond to their dict counterparts
    assert split_folds == [0, 1, 2]

    # each categorical value in the split map above gets one example,
    # plus one out-of-split-map (unseen example)
    counts = [1, 1, 1, 1]

    dummy_data = create_structured_dummy_data(counts)

    split_folds = [ratio_split.partition_fn(ex, ratio_split.get_num_splits())
                   for ex in dummy_data]

    assert ratio_split.get_num_splits() == 4

    # default behavior is assigning everything into eval (index 1)
    assert split_folds == [0, 1, 2, 3]

    # test whether eval assignment works
    ratio_split.unknown_category_policy = "eval"

    # each categorical value in the split map above gets one example,
    # plus one out-of-split-map (unseen example)
    counts = [1, 1, 1, 1]

    dummy_data = create_structured_dummy_data(counts)

    split_folds = [ratio_split.partition_fn(ex, ratio_split.get_num_splits())
                   for ex in dummy_data]

    assert ratio_split.get_num_splits() == 3

    # default behavior is eval (index 1)
    assert split_folds == [0, 1, 2, 1]


def test_categorical_split_ordering(create_structured_dummy_data):
    cat_col = "my_cat_col"

    # real logic begins here
    split_map = {"train": ["value1"],
                 "eval": ["value2"]}

    domain_split = CategoricalDomainSplit(categorical_column=cat_col,
                                          split_map=split_map)

    # each categorical value in the split map above gets one example
    counts = [3, 1]

    dummy_data = create_structured_dummy_data(counts)

    split_folds = [domain_split.partition_fn(ex, domain_split.get_num_splits())
                   for ex in dummy_data]

    # expected: first 3 are 0 (value1, going into train),
    # last is 1 (value2, going into eval)
    assert split_folds == [0, 0, 0, 1]
    assert domain_split.get_split_names() == ["train", "eval", "skip"]

    ################################################
    # NOW: Order reversed, eval comes before train #
    ################################################

    # same split map, fold orders reversed
    split_map = {"eval": ["value2"],
                 "train": ["value1"]}

    domain_split = CategoricalDomainSplit(categorical_column=cat_col,
                                          split_map=split_map)

    # value_1 gets 3 examples, value_2 gets 1 example
    counts = [3, 1]

    dummy_data = create_structured_dummy_data(counts)

    split_folds = [domain_split.partition_fn(ex, domain_split.get_num_splits())
                   for ex in dummy_data]

    # expected: first 3 are 1 (value1, going into train), last is 0 (eval)
    assert split_folds == [1, 1, 1, 0]
    assert domain_split.get_split_names() == ["eval", "train", "skip"]
