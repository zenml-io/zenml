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
"""Implementation of the identity split."""

from typing import Text, List

from zenml.steps.split import BaseSplitStep
from zenml.steps.split import constants


class NoSplit(BaseSplitStep):
    """
    No split function. Use this to pass your entire data forward completely
    unchanged.
    """

    def __init__(
            self,
            statistics=None,
            schema=None,
    ):
        """
        No split constructor.

        Use this to pass your entire data forward completely
        unchanged.

        Args:
            statistics: Parsed statistics from a preceding StatisticsGen.
            schema: Parsed schema from a preceding SchemaGen.
        """
        super().__init__(statistics=statistics, schema=schema)

    def partition_fn(self, element, n):
        """
        Function for no split on data; to be used in a beam.Partition.
        Args:
            element: Data point, given as a tf.train.Example.
            n: Number of splits, unused here.

        Returns:
            An integer n, where 0 ≤ n ≤ num_partitions - 1.
        """
        return 0

    def get_split_names(self) -> List[Text]:
        return [constants.NOSPLIT]
