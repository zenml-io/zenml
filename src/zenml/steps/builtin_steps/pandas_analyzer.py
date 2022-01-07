#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
from typing import Any, List, Optional, Type, Union

import pandas as pd

from zenml.artifacts import SchemaArtifact, StatisticsArtifact
from zenml.steps import Output
from zenml.steps.step_interfaces.base_analyzer_step import (
    BaseAnalyzerConfig,
    BaseAnalyzerStep,
)


class PandasAnalyzerConfig(BaseAnalyzerConfig):
    """Config class for the PandasAnalyzer Config"""

    percentiles: List[float] = [0.25, 0.5, 0.75]
    include: Optional[Union[str, List[Type[Any]]]] = None
    exclude: Optional[Union[str, List[Type[Any]]]] = None


class PandasAnalyzer(BaseAnalyzerStep):
    """Simple step implementation which analyzes a given pd.DataFrame"""

    # Manually defining the type of the output artifacts
    OUTPUT_SPEC = {"statistics": StatisticsArtifact, "schema": SchemaArtifact}

    def entrypoint(  # type: ignore[override]
        self,
        dataset: pd.DataFrame,
        config: PandasAnalyzerConfig,
    ) -> Output(  # type:ignore[valid-type]
        statistics=pd.DataFrame, schema=pd.DataFrame
    ):
        """Main entrypoint function for the pandas analyzer

        Args:
            dataset: pd.DataFrame, the given dataset
            config: the configuration of the step
        Returns:
            the statistics and the schema of the given dataframe
        """
        statistics = dataset.describe(
            percentiles=config.percentiles,
            include=config.include,
            exclude=config.exclude,
        ).T
        schema = dataset.dtypes.to_frame().T.astype(str)
        return statistics, schema
