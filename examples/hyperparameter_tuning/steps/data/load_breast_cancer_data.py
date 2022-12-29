import numpy as np
from sklearn import datasets

from zenml.steps.step_decorator import step
from zenml.steps.step_output import Output


@step
def load_breast_cancer_data() -> Output(X=np.ndarray, y=np.ndarray):
    """Loads Breast Cancer Dataset from Scikit Learn"""
    breast_cancer_data = datasets.load_breast_cancer()
    return breast_cancer_data.data, breast_cancer_data.target
