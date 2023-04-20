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
"""Models used by the Facets integration."""


from typing import Dict, List, Union

import pandas as pd
from pydantic import BaseModel


class FacetsComparison(BaseModel):
    """Facets comparison model.

    Returning this from any step will automatically visualize the datasets
    statistics using Facets.

    Attributes:
        datasets: List of datasets to compare. Should be in the format
            `[{"name": "dataset_name", "table": pd.DataFrame}, ...]`.
    """

    datasets: List[Dict[str, Union[str, pd.DataFrame]]]

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True
