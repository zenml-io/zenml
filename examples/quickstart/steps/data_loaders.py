import numpy as np
import pandas as pd
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split

from zenml.steps import Output, step


@step
def training_data_loader() -> Output(
    X_train=pd.DataFrame,
    X_test=pd.DataFrame,
    y_train=pd.Series,
    y_test=pd.Series,
):
    """Load the iris dataset as tuple of Pandas DataFrame / Series."""
    iris = load_iris(as_frame=True)
    X_train, X_test, y_train, y_test = train_test_split(
        iris.data, iris.target, test_size=0.2, shuffle=True, random_state=42
    )
    return X_train, X_test, y_train, y_test


@step
def inference_data_loader() -> pd.DataFrame:
    """Load some (random) inference data."""
    return pd.DataFrame(
        data=np.random.rand(10, 4) * 10,  # assume range [0, 10]
        columns=load_iris(as_frame=True).data.columns,
    )
