# 


from typing import Union

import pandas as pd


class NADropper:
    """Support class to drop NA values in sklearn Pipeline."""

    def fit(self, *args, **kwargs):
        return self

    def transform(self, X: Union[pd.DataFrame, pd.Series]):
        return X.dropna()


class ColumnsDropper:
    """Support class to drop specific columns in sklearn Pipeline."""

    def __init__(self, columns):
        self.columns = columns

    def fit(self, *args, **kwargs):
        return self

    def transform(self, X: Union[pd.DataFrame, pd.Series]):
        return X.drop(columns=self.columns)


class DataFrameCaster:
    """Support class to cast type back to pd.DataFrame in sklearn Pipeline."""

    def __init__(self, columns):
        self.columns = columns

    def fit(self, *args, **kwargs):
        return self

    def transform(self, X):
        return pd.DataFrame(X, columns=self.columns)
