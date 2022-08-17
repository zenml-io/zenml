import pandas as pd
from sklearn.base import ClassifierMixin

from zenml.steps import step


@step
def evaluator(
    X_test: pd.DataFrame,
    y_test: pd.Series,
    model: ClassifierMixin,
) -> float:
    """Calculate the accuracy on the test set"""
    test_acc = model.score(X_test.to_numpy(), y_test.to_numpy())
    print(f"Test accuracy: {test_acc}")
    return test_acc
