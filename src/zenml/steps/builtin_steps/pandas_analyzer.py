#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
from typing import List, Type, Union

import pandas as pd

from zenml.artifacts import SchemaArtifact, StatisticsArtifact
from zenml.steps import Output
from zenml.steps.step_interfaces.base_analyzer_step import (
    BaseAnalyzerConfig,
    BaseAnalyzerStep,
)


class PandasAnalyzerConfig(BaseAnalyzerConfig):
    percentiles: List[Union[int, float]] = [0.25, 0.5, 0.75]
    include: Union[str, List[Type]] = None
    exclude: Union[str, List[Type]] = None


class PandasAnalyzer(BaseAnalyzerStep):
    OUTPUT_SPEC = {"statistics": StatisticsArtifact, "schema": SchemaArtifact}

    def entrypoint(
        self,
        dataset: pd.DataFrame,
        config: PandasAnalyzerConfig,
    ) -> Output(statistics=pd.DataFrame, schema=pd.DataFrame):
        statistics = dataset.describe(
            percentiles=config.percentiles,
            include=config.include,
            exclude=config.exclude,
        ).T
        schema = dataset.dtypes.to_frame().T.astype(str)
        return statistics, schema
