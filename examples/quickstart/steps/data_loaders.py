import numpy as np

from zenml.integrations.sklearn.helpers.digits import get_digits
from zenml.steps import Output, step


@step
def training_data_loader() -> Output(
    X_train=np.ndarray, X_test=np.ndarray, y_train=np.ndarray, y_test=np.ndarray
):
    """Loads the digits dataset as normal numpy arrays."""
    X_train, X_test, y_train, y_test = get_digits()
    return X_train, X_test, y_train, y_test


@step
def inference_data_loader() -> np.ndarray:
    """Load some (random) inference data."""
    return np.random.rand(1, 64)  # flattened 8x8 random noise image
