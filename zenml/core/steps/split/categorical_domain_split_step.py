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
"""Implementation of the categorical domain split."""

from typing import Text, Dict, List, Any

from zenml.core.steps.split import constants
from zenml.core.steps.split.base_split_step import BaseSplitStep
from zenml.core.steps.split.utils import get_categorical_value


def lint_split_map(split_map: Dict[Text, List[Text]]):
    """Small utility to lint the split_map"""
    if constants.TRAIN not in split_map.keys():
        raise AssertionError(f'You have to define some values for '
                             f'the {constants.TRAIN} split.')
    if len(split_map) <= 1:
        raise AssertionError('Please specify more than 1 split name in the '
                             'split_map!')


def CategoricalPartitionFn(element: Any,
                           num_partitions: int,
                           categorical_column: Text,
                           split_map: Dict[Text, List[Text]]) -> int:
    """
    Function for a categorical split on data to be used in a beam.Partition.
    Args:
        element: Data point, given as a tf.train.Example.
        num_partitions: Number of splits, unused here.
        categorical_column: Name of the categorical column in the data on which
        to perform the split.
        split_map: Dict {split_name: [category_list]} mapping the categorical
        values in categorical_column to their respective splits.

    Returns: An integer n, where 0 <= n <= num_partitions - 1.

    """
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
            categorical_column: Text,
            split_map: Dict[Text, List[Text]],
            statistics=None,
            schema=None,
    ):
        """

        Args:
            statistics: Parsed statistics artifact from a preceding
            StatisticsGen.
            schema: Parsed schema artifact from a preceding SchemaGen.
            categorical_column: Name of the categorical column in the data on
            which to split.
            split_map: a dict { split_name: [category_values] }.
        """
        self.categorical_column = categorical_column

        lint_split_map(split_map)
        self.split_map = split_map

        super().__init__(statistics=statistics,
                         schema=schema,
                         categorical_column=categorical_column,
                         split_map=split_map)

    def partition_fn(self):
        return CategoricalPartitionFn, {
            'split_map': self.split_map,
            'categorical_column': self.categorical_column
        }

    def get_split_names(self) -> List[Text]:
        return list(self.split_map.keys())
