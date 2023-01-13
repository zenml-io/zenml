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
import os
import re

import numpy as np
import pandas as pd

from zenml.steps import Output, step

TRAIN_PATH = os.path.join(os.path.dirname(__file__), "../../data", "train.csv")
TEST_PATH = os.path.join(os.path.dirname(__file__), "../../data", "test.csv")


def clean_text(text: str):
    return re.sub(r"\W", " ", text.lower())


@step
def importer() -> Output(
    X_train=np.ndarray,
    X_test=np.ndarray,
    y_train=np.ndarray,
    y_test=np.ndarray,
):
    train = pd.read_csv(TRAIN_PATH)
    test = pd.read_csv(TEST_PATH)

    X_train = train["x"].apply(clean_text).to_numpy()
    X_test = test["x"].apply(clean_text).to_numpy()
    y_train = train["y"].to_numpy()
    y_test = test["y"].to_numpy()

    return (X_train, X_test, y_train, y_test)
