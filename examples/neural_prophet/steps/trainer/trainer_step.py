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
import pandas as pd
from neuralprophet import NeuralProphet

from zenml import step
from zenml.logger import get_logger
from zenml.steps import BaseParameters

logger = get_logger(__name__)


class NeuralProphetParameters(BaseParameters):
    """Tracks parameters for a NeuralProphet model."""

    weekly_seasonality: int = 6
    daily_seasonality: int = 10
    trend_reg: int = 1
    learning_rate: int = 0.01


@step
def trainer(
    params: NeuralProphetParameters,
    df_train: pd.DataFrame,
    df_test: pd.DataFrame,
) -> NeuralProphet:
    """Trains a NeuralProphet model on the data."""
    m = NeuralProphet(
        weekly_seasonality=params.weekly_seasonality,
        daily_seasonality=params.daily_seasonality,
        trend_reg=params.trend_reg,
        learning_rate=params.learning_rate,
    )
    metrics = m.fit(df_train, freq="H", validation_df=df_test)
    logger.info(f"Metrics: {metrics}")
    return m
