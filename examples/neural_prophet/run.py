#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

import pandas as pd
from neuralprophet import NeuralProphet

from zenml.integrations.constants import NEURAL_PROPHET
from zenml.logger import get_logger
from zenml.pipelines import pipeline
from zenml.steps import BaseStepConfig, Output, step

logger = get_logger(__name__)

DATA_LOCATION = "https://raw.githubusercontent.com/ourownstory/neuralprophet-data/main/datasets/"


class NeuralProphetConfig(BaseStepConfig):
    """Tracks parameters for a NeuralProphet model"""

    weekly_seasonality: int = 6
    daily_seasonality: int = 10
    trend_reg: int = 1
    learning_rate: int = 0.01


@step
def data_loader() -> Output(df_train=pd.DataFrame, df_test=pd.DataFrame):
    """Return the renewable energy dataset as pandas dataframes."""
    sf_pv_df = pd.read_csv(DATA_LOCATION + "energy/SF_PV.csv")
    df_train, df_test = NeuralProphet().split_df(
        sf_pv_df, freq="H", valid_p=1.0 / 12
    )
    return df_train, df_test


@step
def trainer(
    config: NeuralProphetConfig, df_train: pd.DataFrame, df_test: pd.DataFrame
) -> NeuralProphet:
    """Trains a NeuralProphet model on the data."""
    m = NeuralProphet(
        weekly_seasonality=config.weekly_seasonality,
        daily_seasonality=config.daily_seasonality,
        trend_reg=config.trend_reg,
        learning_rate=config.learning_rate,
    )
    metrics = m.fit(df_train, freq="H", validation_df=df_test)
    logger.info(f"Metrics: {metrics}")
    return m


@step
def predictor(model: NeuralProphet, df: pd.DataFrame) -> pd.DataFrame:
    """Makes predictions on a trained NeuralProphet model."""
    return model.predict(df)


@pipeline(enable_cache=True, required_integrations=[NEURAL_PROPHET])
def neural_prophet_pipeline(
    data_loader,
    trainer,
    predictor,
):
    """Links all the steps together in a pipeline"""
    df_train, df_test = data_loader()
    m = trainer(df_train, df_test)
    predictor(m, df_train)


if __name__ == "__main__":

    pipeline = neural_prophet_pipeline(
        data_loader=data_loader(), trainer=trainer(), predictor=predictor()
    )

    pipeline.run()

    print(
        "Pipeline has run and model is trained. Please run the "
        "`post_execution.ipynb` notebook to inspect the results."
    )
