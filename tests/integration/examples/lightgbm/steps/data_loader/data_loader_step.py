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
from typing import Tuple

import lightgbm as lgb
import numpy as np
import pandas as pd
from typing_extensions import Annotated

from zenml import step

# Shape of the LightGBM regression demo dataset this example used to download
# from GitHub: a scalar target followed by 28 numeric features. The predictor
# step feeds the trained booster 28-column inputs, so keep the width in sync.
NUM_FEATURES = 28
NUM_TRAIN_ROWS = 7000
NUM_TEST_ROWS = 500
RANDOM_SEED = 42


def _make_regression_frame(
    rng: np.random.Generator, num_rows: int, weights: np.ndarray
) -> pd.DataFrame:
    """Builds a frame with the target in column 0 and features after it.

    Args:
        rng: Seeded random generator.
        num_rows: Number of rows to generate.
        weights: Linear weights used to derive the target from the features.

    Returns:
        A frame with integer column labels, matching the layout of the
        original tab-separated demo files (label first, no header).
    """
    features = rng.standard_normal((num_rows, NUM_FEATURES))
    noise = rng.standard_normal(num_rows) * 0.1
    target = features @ weights + noise
    return pd.DataFrame(np.column_stack([target, features]))


@step
def data_loader() -> Tuple[
    Annotated[lgb.Dataset, "mat_train"], Annotated[lgb.Dataset, "mat_test"]
]:
    """Generates a deterministic synthetic regression dataset.

    The example previously downloaded LightGBM's demo files from
    raw.githubusercontent.com without checking the response, so a rate-limited
    or empty reply surfaced as ``pandas.errors.EmptyDataError`` inside the
    pipeline. Generating the data locally keeps the example hermetic.
    """
    rng = np.random.default_rng(RANDOM_SEED)
    weights = rng.standard_normal(NUM_FEATURES)
    df_train = _make_regression_frame(rng, NUM_TRAIN_ROWS, weights)
    df_test = _make_regression_frame(rng, NUM_TEST_ROWS, weights)

    # Parse data
    y_train = df_train[0]
    y_test = df_test[0]
    X_train = df_train.drop(0, axis=1)
    X_test = df_test.drop(0, axis=1)

    # create dataset for lightgbm
    mat_train = lgb.Dataset(X_train, y_train)
    mat_test = lgb.Dataset(X_test, y_test, reference=mat_train)
    return mat_train, mat_test
