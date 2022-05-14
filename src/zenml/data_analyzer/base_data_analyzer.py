#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

from abc import ABC
from typing import Any, ClassVar, List, Optional, Sequence, Union

import pandas as pd

from zenml.enums import StackComponentType
from zenml.stack import StackComponent
from zenml.steps import BaseStepConfig


class BaseDataAnalyzerConfig(BaseStepConfig):
    """Base class for all data analysis configurations"""

    target: Optional[str] = "target"
    prediction: Optional[Union[str, Sequence[str]]] = "prediction"
    datetime: Optional[str] = "datetime"
    id: Optional[str] = None
    numerical_features: Optional[List[str]] = None
    categorical_features: Optional[List[str]] = None
    target_names: Optional[List[str]] = None


class BaseDataAnalyzer(StackComponent, ABC):
    """Base class for all ZenML data analyzers."""

    # Class configuration
    TYPE: ClassVar[StackComponentType] = StackComponentType.DATA_ANALYZER
    FLAVOR: ClassVar[str]

    def analyze(
        self, config: Optional[BaseStepConfig] = None, *args: Any, **kwargs: Any
    ) -> Any:
        """Generic analyze method that accepts all arguments.

        Args:
            config: configuration of the analysis.
        Returns:
            Result of analysis.
        """

    def analyze_tabular(
        self,
        analysis: pd.DataFrame,
        reference: Optional[pd.DataFrame] = None,
        model: Optional[Any] = None,
        config: Optional[BaseStepConfig] = None,
    ) -> Any:
        """Generic method for analyzing pandas dataframes.

        Args:
            config: configuration of the analysis.
            analysis: dataframe to be analyzed.
            reference: optional dataframe which is the reference.
            model: optional model to aid in analysis.
        Returns:
            Result of analysis.
        """
