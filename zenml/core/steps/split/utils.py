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

from typing import Text, List, Dict, Any

import tensorflow as tf


def get_categorical_value(example: tf.train.Example, cat_col: Text):
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

    # TODO: Should we raise here? This could happen in a NULL type situation
    return None


def partition_cat_list(cat_list: List[Text], c_ratio: Dict[Text, Any]):
    """
    Helper to split a category list by the entries in a category split dict.
    Scales well in the number of folds
    """
    cat_dict = {}

    num_cats = len(cat_list)
    ratio = 0

    # This might produce unexpected results if the number of categories
    # is lower than the number of folds.
    for fold, fold_pct in c_ratio.items():
        left_bound = round(num_cats * ratio)
        ratio += fold_pct
        right_bound = round(num_cats * ratio)
        # write categories for fold to the cat_list dict
        cat_dict[fold] = cat_list[left_bound:right_bound]

    return cat_dict
