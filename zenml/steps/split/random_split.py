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

from zenml.steps.split import BaseSplitStep


def lint_split_map(split_map: Dict[Text, float]):
    """Small utility to lint the split_map"""
    if len(split_map) <= 1:
        raise AssertionError('Please specify more than 1 split name in the '
                             'split_map!')

    if not all(isinstance(v, (int, float)) for v in split_map.values()):
        raise AssertionError("Only int or float values are allowed when "
                             "specifying a random split!")


class RandomSplit(BaseSplitStep):
    """
    Random split. Use this to randomly split data based on a cumulative
    distribution function defined by a split_map dict.
    """

    def __init__(
            self,
            split_map: Dict[Text, float],
            statistics=None,
            schema=None,
    ):
        """
        Random split constructor.

        Randomly split the data based on a cumulative distribution function
        defined by split_map.

        Example usage:

        # Split data randomly, but evenly into train, eval and test

        >>> split = RandomSplit(
        ... split_map = {"train": 0.334,
        ...              "eval": 0.333,
        ...              "test": 0.333})

        Here, each data split gets assigned about one third of the probability
        mass. The split is carried out by sampling from the categorical
        distribution defined by the values p_i in the split map, i.e.

        P(index = i) = p_i, i = 1,...,n ;

        where n is the number of splits defined in the split map. Hence, the
        values in the split map must sum up to 1. For more information, see
        https://en.wikipedia.org/wiki/Categorical_distribution.


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

    def partition_fn(self,
                     element: Any,
                     num_partitions: int) -> int:
        """
        Function for a random split of the data; to be used in a beam.Partition.
        This function implements a simple random split algorithm by drawing
        integers from a categorical distribution defined by the values in
        split_map.

        Args:
            element: Data point, in format tf.train.Example.
            num_partitions: Number of splits, unused here.

        Returns:
            An integer n, where 0 ≤ n ≤ num_partitions - 1.
        """

        # calculates probability mass of each split
        probability_mass = np.cumsum(list(self.split_map.values()))
        max_value = probability_mass[-1]

        return bisect.bisect(probability_mass, np.random.uniform(0, max_value))

    def get_split_names(self) -> List[Text]:
        return list(self.split_map.keys())
