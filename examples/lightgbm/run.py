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
import tempfile

import lightgbm as lgb
import numpy as np
import pandas as pd
import requests

from zenml.integrations.constants import LIGHTGBM
from zenml.logger import get_logger
from zenml.pipelines import pipeline
from zenml.steps import BaseStepConfig, Output, step

logger = get_logger(__name__)

TRAIN_SET_RAW = "https://raw.githubusercontent.com/microsoft/LightGBM/master/examples/regression/regression.train"
TEST_SET_RAW = "https://raw.githubusercontent.com/microsoft/LightGBM/master/examples/regression/regression.test"


class LightGBMConfig(BaseStepConfig):
    boosting_type: str = "gbdt"
    objective: str = "regression"
    num_leaves: int = 31
    learning_rate: float = 0.05
    feature_fraction: float = 0.9
    bagging_fraction: float = 0.8
    bagging_freq: int = 5
    verbose: int = 0


@step
def data_loader() -> Output(mat_train=lgb.Dataset, mat_test=lgb.Dataset):
    """Retrieves the data from the demo directory of the LightGBM repo."""
    # Write data to temporary files to load it with `lgb.Dataset`.
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".html", encoding="utf-8"
    ) as f:
        f.write(requests.get(TRAIN_SET_RAW).text)
        df_train = pd.read_csv(f.name, header=None, sep="\t")

    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".html", encoding="utf-8"
    ) as f:
        f.write(requests.get(TEST_SET_RAW).text)
        df_test = pd.read_csv(f.name, header=None, sep="\t")

    # Parse data
    y_train = df_train[0]
    y_test = df_test[0]
    X_train = df_train.drop(0, axis=1)
    X_test = df_test.drop(0, axis=1)

    # create dataset for lightgbm
    mat_train = lgb.Dataset(X_train, y_train)
    mat_test = lgb.Dataset(X_test, y_test, reference=mat_train)
    return mat_train, mat_test


@step
def trainer(
    config: LightGBMConfig, mat_train: lgb.Dataset, mat_test: lgb.Dataset
) -> lgb.Booster:
    """Trains a LightGBM model on the data."""
    params = {
        "boosting_type": config.boosting_type,
        "objective": config.objective,
        "num_leaves": config.num_leaves,
        "learning_rate": config.learning_rate,
        "feature_fraction": config.feature_fraction,
        "bagging_fraction": config.bagging_fraction,
        "bagging_freq": config.bagging_freq,
        "verbose": config.verbose,
    }
    gbm = lgb.train(
        params,
        mat_train,
        num_boost_round=20,
        valid_sets=mat_test,
        callbacks=[lgb.early_stopping(stopping_rounds=5)],
    )
    return gbm


@step
def predictor(model: lgb.Booster, mat: lgb.Dataset) -> np.ndarray:
    """Makes predictions on a trained LightGBM booster model."""
    return model.predict(np.random.rand(7, 28))


@pipeline(enable_cache=False, required_integrations=[LIGHTGBM])
def lgbm_pipeline(
    data_loader,
    trainer,
    predictor,
):
    """Links all the steps together in a pipeline"""
    mat_train, mat_test = data_loader()
    model = trainer(mat_train, mat_test)
    predictor(model, mat_train)


if __name__ == "__main__":

    pipeline = lgbm_pipeline(
        data_loader=data_loader(), trainer=trainer(), predictor=predictor()
    )
    pipeline.run()
