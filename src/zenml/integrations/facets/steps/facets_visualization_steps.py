#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Facets Standard Steps."""

from typing import Dict, List, Union

import pandas as pd

from zenml import step
from zenml.integrations.facets.models import FacetsComparison


@step
def facets_visualization_step(
    reference: pd.DataFrame, comparison: pd.DataFrame
) -> FacetsComparison:
    """Visualize and compare dataset statistics with Facets.

    Args:
        reference: Reference dataset.
        comparison: Dataset to compare to reference.

    Returns:
        `FacetsComparison` object.
    """
    return FacetsComparison(
        datasets=[
            {"name": "reference", "table": reference},
            {"name": "comparison", "table": comparison},
        ]
    )


@step
def facets_list_visualization_step(
    dataframes: List[pd.DataFrame],
) -> FacetsComparison:
    """Visualize and compare dataset statistics with Facets.

    Args:
        dataframes: List of dataframes whose statistics should be compared.

    Returns:
        `FacetsComparison` object.
    """
    datasets: List[Dict[str, Union[str, pd.DataFrame]]] = []
    for i, df in enumerate(dataframes):
        datasets.append({"name": f"dataset_{i}", "table": df})
    return FacetsComparison(datasets=datasets)


@step
def facets_dict_visualization_step(
    dataframes: Dict[str, pd.DataFrame],
) -> FacetsComparison:
    """Visualize and compare dataset statistics with Facets.

    Args:
        dataframes: Dict of dataframes whose statistics should be compared,
            mapping names to dataframes.

    Returns:
        `FacetsComparison` object.
    """
    datasets: List[Dict[str, Union[str, pd.DataFrame]]] = []
    for name, df in dataframes.items():
        datasets.append({"name": name, "table": df})
    return FacetsComparison(datasets=datasets)
