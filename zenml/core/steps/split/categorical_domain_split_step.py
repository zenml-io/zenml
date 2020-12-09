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

from typing import Text, List

import apache_beam as beam
import tensorflow as tf

from zenml.core.steps.split import constants
from zenml.core.steps.split.base_split_step import BaseSplitStep


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


def lint_split_map(split_map):
    """Small utility to lint the split_map"""
    if constants.TRAIN not in split_map.keys():
        raise AssertionError(f'You have to define some values for '
                             f'the {constants.TRAIN} split.')
    if len(split_map) <= 1:
        raise AssertionError('Please specify more than 1 split name in the '
                             'split_map!')


def CategoricalPartitionFn(
        element,
        num_partitions: int,
        categorical_column,
        split_map,
):
    category_value = get_categorical_value(element, cat_col=categorical_column)

    # The following code produces a dict: { split_name: unique_integer }
    # However 'train' always maps to 0
    enumerated_splits = {constants.TRAIN: 0}
    enumerated_splits.update(
        {name: i for i, name in enumerate(split_map.keys())
         if name != constants.TRAIN}
    )

    for split_name, category_value_list in split_map.items():
        # if the value is in the list, then just return
        if category_value in category_value_list:
            # return the index of that split
            return enumerated_splits[split_name]

    # This is the default behavior for category_values that dont belong to 
    #  any split in the split_map. We assign it to index '1'
    return 1


class CategoricalDomainSplitStep(BaseSplitStep):

    def __init__(
            self,
            categorical_column,
            split_map,
            statistics = None,
            schema = None,
    ):
        """

        Args:
            statistics:
            schema:
            categorical_column:
            split_map: a dict { split_name: [category_values] }
        """
        self.categorical_column = categorical_column

        lint_split_map(split_map)
        self.split_map = split_map

        super().__init__(statistics, schema)

    def partition_fn(self):
        return CategoricalPartitionFn, {
            'split_map': self.split_map,
            'categorical_column': self.categorical_column
        }

    def get_split_names(self) -> List[Text]:
        return list(self.split_map.keys())
