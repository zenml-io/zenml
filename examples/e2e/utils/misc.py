import string

import pandas as pd
from sklearn.datasets import make_classification


def gen_data(n_samples: int):
    n_features = 20
    X, y = make_classification(
        n_samples=n_samples,
        n_features=n_features,
        n_classes=2,
        random_state=42,
    )
    dataset = pd.concat(
        [
            pd.DataFrame(X, columns=list(string.ascii_uppercase[:n_features])),
            pd.Series(y, name="target"),
        ],
        axis=1,
    )
    return dataset
