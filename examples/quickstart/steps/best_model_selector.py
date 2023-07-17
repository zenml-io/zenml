from typing import Tuple

import pandas as pd
from sklearn.base import ClassifierMixin
from typing_extensions import Annotated

from zenml import step


@step
def best_model_selector(
    X_test: pd.DataFrame,
    y_test: pd.Series,
    model1: ClassifierMixin,
    model2: ClassifierMixin,
) -> Tuple[
    Annotated[ClassifierMixin, "best_model"],
    Annotated[float, "best_model_test_acc"],
]:
    """Calculate the accuracy on the test set and return the best model and its accuracy."""
    test_acc1 = model1.score(X_test.to_numpy(), y_test.to_numpy())
    test_acc2 = model2.score(X_test.to_numpy(), y_test.to_numpy())
    print(f"Test accuracy ({model1.__class__.__name__}): {test_acc1}")
    print(f"Test accuracy ({model2.__class__.__name__}): {test_acc2}")
    if test_acc1 > test_acc2:
        best_model = model1
        best_model_test_acc = test_acc1
    else:
        best_model = model2
        best_model_test_acc = test_acc2
    return best_model, best_model_test_acc
