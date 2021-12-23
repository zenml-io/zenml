import pandas as pd
from sklearn import datasets

from evidently.dashboard import Dashboard
from evidently.tabs import DataDriftTab

iris = datasets.load_iris()
iris_frame = pd.DataFrame(iris.data, columns=iris.feature_names)
iris_frame["target"] = iris.target
