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

from typing import Dict, Text, Any, List, Union

from zenml import Split, Index, Categorize


def no_split() -> Split:
    """Helper function to create a no-split configuration"""
    return Split()


def index_split(by: Text,
                ratio: Dict[Text, Any] = None) -> Split:
    """Helper function to create a indexed split configuration

    Args:
        by (Text): name of the column to index by
        ratio: dict to define the splits, e.g. {"train":0.8, "eval":0.2}

    Returns:
        an instance of Split with the proper configuration
    """
    return Split(index=Index(by=by, ratio=ratio))


def category_split(by: Text,
                   ratio: Dict[Text, Any] = None,
                   categories: Union[Dict, List] = None) -> Split:
    """Helper function to create a categorical split configuration

    Args:
        by (Text): name of the column to categorize by
        ratio: dict to define the splits, e.g. {"train":0.8, "eval":0.2}
        categories: dict or list to define the categories

    Returns:
        an instance of Split with the proper configuration
    """
    return Split(categorize=Categorize(by=by,
                                       ratio=ratio,
                                       categories=categories))


def hybrid_split(index_by: Text,
                 category_by: Text,
                 index_ratio: Dict[Text, Any] = None,
                 category_ratio: Dict[Text, Any] = None) -> Split:
    """Helper function to create a hybrid split configuration with both index
    and categorical elements

    Args:
        index_by (Text): name of the column to index by
        category_by (Text): name of the column to categorize by
        index_ratio: dict to define the index split ratios
        category_ratio: dict to define the category split ratios

    Returns:
        an instance of Split with the proper configuration
    """
    return Split(index=Index(by=index_by, ratio=index_ratio),
                 categorize=Categorize(by=category_by, ratio=category_ratio))
