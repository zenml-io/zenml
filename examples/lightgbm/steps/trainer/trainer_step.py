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

from zenml.steps import BaseParameters, step


class LightGBMParameters(BaseParameters):
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
    params: LightGBMParameters, mat_train: lgb.Dataset, mat_test: lgb.Dataset
) -> lgb.Booster:
    """Trains a LightGBM model on the data."""
    params = {
        "boosting_type": params.boosting_type,
        "objective": params.objective,
        "num_leaves": params.num_leaves,
        "learning_rate": params.learning_rate,
        "feature_fraction": params.feature_fraction,
        "bagging_fraction": params.bagging_fraction,
        "bagging_freq": params.bagging_freq,
        "verbose": params.verbose,
    }
    gbm = lgb.train(
        params,
        mat_train,
        num_boost_round=20,
        valid_sets=mat_test,
        callbacks=[lgb.early_stopping(stopping_rounds=5)],
    )
    return gbm
