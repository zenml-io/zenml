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
from neural_prophet import NeuralProphet

from zenml.integrations.constants import NEURAL_PROPHET
from zenml.logger import get_logger
from zenml.pipelines import pipeline
from zenml.repository import Repository
from zenml.steps import Output, step

logger = get_logger(__name__)

@step
def data_loader() -> Output(df_train=pd.DataFrame, df_test=pd.DataFrame):
    """Return the renewable."""
    data_location = "https://raw.githubusercontent.com/ourownstory/neuralprophet-data/main/datasets/"
    sf_pv_df = pd.read_csv(data_location +  'energy/SF_PV.csv')
    df_train, df_test = NeuralProphet().split_df(sf_pv_df, freq='H', valid_p = 1.0/12)
    return df_train, df_test

@step
def trainer(df_train: pd.DataFrame, df_test: pd.DataFrame) -> NeuralProphet:
    m = NeuralProphet(
        weekly_seasonality=6,
        daily_seasonality=10,
        trend_reg=1,
        learning_rate=0.01,
    )
    metrics = m.fit(df_train, freq='H', validation_df=df_test)
    print(metrics)
    return m

@step
def predicter(model: NeuralProphet, df: pd.DataFrame) -> pd.DataFrame:
    return model.predict(df)


@pipeline(enable_cache=True, required_integrations=[NEURAL_PROPHET])
def neural_prophet_pipeline(
    data_loader,
    trainer,
    predicter,
):
    """Links all the steps together in a pipeline"""
    df_train, df_test = data_loader()
    m = trainer(df_train, df_test)
    predicter(m, df_train)

if __name__ == "__main__":

    pipeline = neural_prophet_pipeline(
        data_loader=data_loader(),
        trainer=trainer(),
        predicter=predicter()
    )

    pipeline.run()

    repo = Repository()
    pipe = repo.get_pipelines()[-1]
    model = pipe.runs[-1].get_step(name='trainer').output.read()
