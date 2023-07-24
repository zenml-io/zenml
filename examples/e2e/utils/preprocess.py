from typing import Union

import pandas as pd


class NADropper:
    def fit(self, *args, **kwargs):
        return self

    def transform(self, X: Union[pd.DataFrame, pd.Series]):
        return X.dropna()


class ColumnsDropper:
    def __init__(self, columns):
        self.columns = columns

    def fit(self, *args, **kwargs):
        return self

    def transform(self, X: Union[pd.DataFrame, pd.Series]):
        return X.drop(columns=self.columns)
