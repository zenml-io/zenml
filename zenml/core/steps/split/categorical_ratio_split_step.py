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

from typing import Text, List, Dict

from zenml.core.steps.split import constants
from zenml.core.steps.split.base_split_step import BaseSplitStep
from zenml.core.steps.split.categorical_domain_split_step import \
    CategoricalPartitionFn
from zenml.core.steps.split.utils import partition_cat_list


def lint_split_map(split_map: Dict[Text, float]):
    """Small utility to lint the split_map"""
    if constants.TRAIN not in split_map.keys():
        raise AssertionError(f'You have to define some values for '
                             f'the {constants.TRAIN} split.')
    if len(split_map) <= 1:
        raise AssertionError('Please specify more than 1 split name in the '
                             'split_map!')


class CategoricalRatioSplitStep(BaseSplitStep):

    def __init__(
            self,
            categorical_column: Text,
            categories: List[Text],
            split_ratio: Dict[Text, float],
            statistics=None,
            schema=None,
    ):
        """

        Args:
            statistics: Parsed statistics from a preceding StatisticsGen.
            schema: Parsed schema from a preceding SchemaGen.
            categorical_column: Name of the categorical column used for
                                splitting.
            split_ratio: A dict { split_name: percentage of categories
                                    in split }.
        """
        self.categorical_column = categorical_column

        split_map = partition_cat_list(categories, split_ratio)
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
