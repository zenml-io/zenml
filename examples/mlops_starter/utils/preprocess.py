# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2025. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from typing import Sequence, Union

import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


class NADropper(TransformerMixin, BaseEstimator):
    """Support class to drop NA values in sklearn Pipeline."""

    def fit(self, X, y=None):
        self.is_fitted_ = True
        return self

    def transform(self, X: Union[pd.DataFrame, pd.Series]):
        return X.dropna()


class ColumnsDropper(TransformerMixin, BaseEstimator):
    """Support class to drop specific columns in sklearn Pipeline."""

    def __init__(self, columns: Sequence[str]):
        self.columns = list(columns)

    def fit(self, X, y=None):
        self.is_fitted_ = True
        return self

    def transform(self, X: Union[pd.DataFrame, pd.Series]):
        return X.drop(columns=self.columns)


class DataFrameCaster(TransformerMixin, BaseEstimator):
    """Support class to cast type back to pd.DataFrame in sklearn Pipeline."""

    def __init__(self, columns: Sequence[str]):
        self.columns = list(columns)

    def fit(self, X, y=None):
        # Set fitted attributes so sklearn can recognize this transformer as fitted.
        # (newer sklearn calls check_is_fitted on the Pipeline's final step)
        self.n_features_in_ = X.shape[1] if hasattr(X, "shape") else None
        self.is_fitted_ = True
        return self

    def transform(self, X):
        return pd.DataFrame(X, columns=self.columns)
