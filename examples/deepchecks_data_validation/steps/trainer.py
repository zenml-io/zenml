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
from sklearn.base import ClassifierMixin
from sklearn.ensemble import RandomForestClassifier

from zenml.steps import step

LABEL_COL = "target"


@step
def trainer(df_train: pd.DataFrame) -> ClassifierMixin:
    rf_clf = RandomForestClassifier(random_state=0)
    rf_clf.fit(df_train.drop(LABEL_COL, axis=1), df_train[LABEL_COL])
    return rf_clf
