import numpy as np
from sklearn import datasets

from zenml.steps.step_decorator import step
from zenml.steps.step_output import Output


@step
def load_iris_data() -> Output(X=np.ndarray, y=np.ndarray):
    """Loads Iris Dataset from Scikit Learn"""
    iris = datasets.load_iris()
    return iris.data[:, :3], iris.target
