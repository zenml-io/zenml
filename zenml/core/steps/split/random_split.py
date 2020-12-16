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
"""Implementation of a random split of the input data set."""

import bisect
from typing import Text, List, Dict, Any

import numpy as np

from zenml.core.steps.split import constants
from zenml.core.steps.split.base_split_step import BaseSplitStep


def lint_split_map(split_map: Dict[Text, float]):
    """Small utility to lint the split_map"""
    if constants.TRAIN not in split_map.keys():
        raise AssertionError(f'You have to define some values for '
                             f'the {constants.TRAIN} split.')
    if len(split_map) <= 1:
        raise AssertionError('Please specify more than 1 split name in the '
                             'split_map!')

    if not all(isinstance(v, float) for v in split_map.values()):
        raise AssertionError("Only float values are allowed when specifying "
                             "a random split!")


def RandomSplitPartitionFn(element: Any,
                           num_partitions: int,
                           split_map: Dict[Text, float]) -> int:
    """
    Function for a random split of the data; to be used in a beam.Partition.
    Args:
        element: Data point, in format tf.train.Example.
        num_partitions: Number of splits, unused here.
        split_map: Dict mapping {split_name: percentage of data in split}.

    Returns: An integer n, where 0 <= n <= num_partitions - 1.
    """

    # calculates probability mass of each split (= interval on [0,1))
    probability_mass = np.cumsum(list(split_map.values()))

    # excludes the right bound 1 as it is redundant
    brackets = probability_mass[:-1]

    return bisect.bisect(brackets, np.random.rand())


class RandomSplitStep(BaseSplitStep):

    def __init__(
            self,
            split_map: Dict[Text, float],
            statistics=None,
            schema=None,
    ):
        """
        Randomly split the data based on split_map.

        Args:
            statistics: Parsed statistics from a preceding StatisticsGen.
            schema: Parsed schema from a preceding SchemaGen.
            split_map: A dict { split_name: percentage of data in split }.
        """

        lint_split_map(split_map)
        self.split_map = split_map

        super().__init__(statistics=statistics,
                         schema=schema,
                         split_map=split_map)

    def partition_fn(self):
        return RandomSplitPartitionFn, {
            'split_map': self.split_map
        }

    def get_split_names(self) -> List[Text]:
        return list(self.split_map.keys())
