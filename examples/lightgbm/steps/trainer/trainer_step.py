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
import lightgbm as lgb

from zenml.steps import BaseStepConfig, step


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
