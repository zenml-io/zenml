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

from typing import Text, Dict, List, Any, Union

from zenml.steps.split import constants
from zenml.steps.split import BaseSplitStep
from zenml.steps.split.utils import get_categorical_value

CategoricalValue = Union[Text, int]


def lint_split_map(split_map: Dict[Text, List[CategoricalValue]]):
    """Small utility to lint the split_map"""
    if len(split_map) <= 1:
        raise AssertionError('Please specify more than 1 split name in the '
                             'split_map!')


class CategoricalDomainSplit(BaseSplitStep):
    """
    Categorical domain split. Use this to split data based on values in
    a single categorical column. A categorical column is defined here as a
    column with finitely many values of type `integer` or `string`.
    """

    def __init__(
            self,
            categorical_column: Text,
            split_map: Dict[Text, List[CategoricalValue]],
            unknown_category_policy: Text = constants.SKIP,
            statistics=None,
            schema=None,
    ):
        """
        Categorical domain split constructor.

        Use this class to split your data based on values in
        a single categorical column. A categorical column is defined here as a
        column with finitely many values of type `integer` or `string`.

        Example usage:

        # Split on a categorical attribute called "color".

        # red and blue datapoints go into the train set,
           green and yellow ones go into the eval set. Other colors,
           e.g. "purple", are discarded due to the "skip" flag.

        >>> split = CategoricalDomainSplit(
        ... categorical_column="color",
        ... split_map = {"train": ["red", "blue"],
        ...              "eval": ["green", "yellow"]},
        ... unknown_category_policy="skip")

        Supply the ``unknown_category_policy`` flag to set the unknown
        category handling policy. There are two main options:

        Setting ``unknown_category_policy`` to any key in the split map
        indicates that any missing categories should be put into that
        particular split. For example, supplying
        ``unknown_category_policy="train"`` indicates that all missing
        categories should go into the training dataset, while
        ``unknown_category_policy="eval"`` indicates that all missing
        categories should go into the evaluation dataset.

        Setting ``unknown_category_policy="skip"`` indicates that data points
        with unknown categorical values (i.e., values not present in any of the
        categorical value lists inside the split map) should be taken out of
        the data set.

        Args:
            statistics: Parsed statistics artifact from a preceding
             StatisticsGen.
            schema: Parsed schema artifact from a preceding SchemaGen.
            categorical_column: Name of the categorical column in the data on
             which to split.
            split_map: A dict { split_name: [categorical_values] } mapping
             categorical values to their respective splits.
            unknown_category_policy: String, indicates how to handle categories
             in the data that are not present in the split map.
        """
        self.categorical_column = categorical_column

        lint_split_map(split_map)
        self.split_map = split_map

        if unknown_category_policy in self.split_map:
            self.unknown_category_policy = unknown_category_policy
        else:
            self.unknown_category_policy = constants.SKIP

        super().__init__(statistics=statistics,
                         schema=schema,
                         categorical_column=categorical_column,
                         split_map=split_map,
                         unknown_category_policy=unknown_category_policy)

    def partition_fn(self,
                     element: Any,
                     num_partitions: int) -> int:

        """
        Function for a categorical split on data to be used in a beam.Partition.
        Args:
            element: Data point, given as a tf.train.Example.
            num_partitions: Number of splits, unused here.

        Returns:
            An integer n, where 0 ≤ n ≤ num_partitions - 1.

        """

        category_value = get_categorical_value(element,
                                               cat_col=self.categorical_column)

        # The following code produces a dict: { split_name: unique_integer }
        enumerated_splits = {name: i for i, name in enumerate(self.split_map.keys())}

        if self.unknown_category_policy not in enumerated_splits:
            enumerated_splits.update({self.unknown_category_policy: num_partitions - 1})

        for split_name, category_value_list in self.split_map.items():
            # if the value is in the list, then just return
            if category_value in category_value_list:
                # return the index of that split
                return enumerated_splits[split_name]

        # This is the default behavior for category_values that dont belong to
        #  any split in the split_map.
        return enumerated_splits[self.unknown_category_policy]

    def get_split_names(self) -> List[Text]:
        split_names = list(self.split_map.keys())
        if self.unknown_category_policy in self.split_map:
            return split_names
        else:
            return split_names + [constants.SKIP]
