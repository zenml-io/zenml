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
"""Some split step utilities are implemented here."""

from typing import Text, List, Dict, Union

import tensorflow as tf

CategoricalValue = Union[Text, int]


def get_categorical_value(example: tf.train.Example, cat_col: Text):
    """
    Helper function to get the categorical value from a tf.train.Example.

    Args:
        example: tf.train.Example, data point in proto format.
        cat_col: Name of the categorical feature of which to extract the
        value from.

    Returns:
        value: The categorical value found in the `cat_col` feature inside
        the tf.train.Example.

    Raises:
        AssertionError: If the `cat_col` feature is not present in the
        tf.train.Example.
    """

    cat_feature = example.features.feature[cat_col]

    possible_types = ["bytes", "float", "int64"]

    for datatype in possible_types:
        value_list = getattr(cat_feature, datatype + "_list")

        if value_list.value:
            value = value_list.value[0]
            if hasattr(value, "decode"):
                return value.decode()
            else:
                return value

    raise AssertionError(f"Error: Feature {cat_col} does not exist in "
                         f"this data.")


def partition_cat_list(cat_list: List[CategoricalValue],
                       c_ratio: Dict[Text, float]):
    """
    Helper to split a category list by the entries in a category split dict.

    Args:
        cat_list: List of categorical values found in the categorical column.
        c_ratio: Dict {fold: ratio} mapping the ratio of all categories to
         split folds.

    Returns:
        cat_dict: Dict {fold: categorical_list} mapping lists of categorical
         values in the data to their designated split folds.
    """

    cat_dict = {}

    num_cats = len(cat_list)
    sum_ratios = sum(c_ratio.values())
    ratio = 0

    # This might produce unexpected results if the number of categories
    # is lower than the number of folds.
    for fold, fold_pct in c_ratio.items():
        left_bound = round(num_cats * ratio)
        ratio += fold_pct / sum_ratios
        right_bound = round(num_cats * ratio)
        # write categories for fold to the cat_list dict
        cat_dict[fold] = cat_list[left_bound:right_bound]

    return cat_dict
