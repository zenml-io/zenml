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
"""Implementation of the ratio-based categorical split."""

from typing import Text, List, Dict, Union

from zenml.core.steps.split import constants
from zenml.core.steps.split.base_split_step import BaseSplit
from zenml.core.steps.split.categorical_domain_split_step import \
    CategoricalPartitionFn
from zenml.core.steps.split.utils import partition_cat_list

CategoricalValue = Union[Text, int]


def lint_split_map(split_map: Dict[Text, float]):
    """Small utility to lint the split_map"""
    if constants.TRAIN not in split_map.keys():
        raise AssertionError(f'You have to define some values for '
                             f'the {constants.TRAIN} split.')
    if len(split_map) <= 1:
        raise AssertionError('Please specify more than 1 split name in the '
                             'split_map!')


class CategoricalRatioSplit(BaseSplit):
    """
    Categorical ratio split. Use this to split data based on a list of values
    of interest in a single categorical column. A categorical column is
    defined here as a column with finitely many values of type `integer` or
    `string`. In contrast to the categorical domain split, here categorical
    values are assigned to different splits by the corresponding percentages,
    defined inside a split ratio object.
    """

    def __init__(
            self,
            categorical_column: Text,
            categories: List[CategoricalValue],
            split_ratio: Dict[Text, float],
            statistics=None,
            schema=None,
    ):
        """
        Categorical domain split constructor.

        Use this class to split your data based on values in
        a single categorical column. A categorical column is defined here as a
        column with finitely many values of type `integer` or `string`.

        Example usage:

        # Split on a categorical attribute called "color", with a defined list
        of categories of interest

        # half of the categories go entirely into the train set,
          the other half into the eval set

        >>> split = CategoricalRatioSplit(
        ... categorical_column="color",
        ... categories = ["red", "green", "blue", "yellow"],
        ... split_ratio = {"train": 0.5,
        ...                "eval": 0.5})

        Any data point with a categorical value that is not present in the
        `categories` list will by default be put into the eval set.

        Args:
            statistics: Parsed statistics from a preceding StatisticsGen.
            schema: Parsed schema from a preceding SchemaGen.
            categorical_column: Name of the categorical column used for
             splitting.
            categories: List of categorical values found in the categorical
             column on which to split.
            split_ratio: A dict mapping { split_name: percentage of categories
                                    in split }.
        """
        self.categorical_column = categorical_column

        split_map = partition_cat_list(categories, split_ratio)
        lint_split_map(split_map)
        self.split_map = split_map

        super().__init__(statistics=statistics,
                         schema=schema,
                         categorical_column=categorical_column,
                         split_ratio=split_ratio,
                         categories=categories)

    def partition_fn(self):
        return CategoricalPartitionFn, {
            'split_map': self.split_map,
            'categorical_column': self.categorical_column
        }

    def get_split_names(self) -> List[Text]:
        return list(self.split_map.keys())
