from typing import Tuple

import pandas as pd
from sklearn.model_selection import train_test_split

from zenml import step


@step
def training_data_loader() -> (
    Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]
):
    """Load the Census Income dataset as tuple of Pandas DataFrame / Series."""
    # Load the dataset
    url = "https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data"
    column_names = [
        "age",
        "workclass",
        "fnlwgt",
        "education",
        "education-num",
        "marital-status",
        "occupation",
        "relationship",
        "race",
        "sex",
        "capital-gain",
        "capital-loss",
        "hours-per-week",
        "native-country",
        "income",
    ]
    data = pd.read_csv(
        url, names=column_names, na_values="?", skipinitialspace=True
    )

    # Drop rows with missing values
    data = data.dropna()

    # Encode categorical features and drop original columns
    categorical_cols = [
        "workclass",
        "education",
        "marital-status",
        "occupation",
        "relationship",
        "race",
        "sex",
        "native-country",
    ]
    data = pd.get_dummies(data, columns=categorical_cols, drop_first=True)

    # Encode target feature
    data["income"] = data["income"].apply(
        lambda x: 1 if x.strip() == ">50K" else 0
    )

    # Separate features and target
    X = data.drop("income", axis=1)
    y = data["income"]

    # Split the dataset into train and test sets
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    return (X_train, X_test, y_train, y_test)
