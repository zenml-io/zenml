import modin.pandas as pd
from sklearn.base import ClassifierMixin
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC

from zenml.pipelines import pipeline
from zenml.steps import Output, step


@step
def simple_data_splitter() -> Output(
    train_set=pd.DataFrame, test_set=pd.DataFrame
):
    # Load the wine dataset
    dataset = load_wine(as_frame=True).frame

    # Split the dataset into training and dev subsets
    train_set, test_set = train_test_split(
        dataset,
    )
    return pd.DataFrame(train_set), pd.DataFrame(test_set)


@step
def simple_svc_trainer(
    train_set: pd.DataFrame,
    test_set: pd.DataFrame,
) -> ClassifierMixin:
    """Trains a sklearn SVC classifier."""
    X_train, y_train = train_set.drop("target", axis=1), train_set["target"]
    X_test, y_test = test_set.drop("target", axis=1), test_set["target"]
    model = SVC(gamma=0.001)
    model.fit(X_train, y_train)
    test_acc = model.score(X_test, y_test)
    print(f"Test accuracy: {test_acc}")
    return model


@pipeline(enable_cache=False)
def first_pipeline(step_1, step_2):
    train_set, test_set = step_1()
    step_2(train_set, test_set)


first_pipeline_instance = first_pipeline(
    step_1=simple_data_splitter(),
    step_2=simple_svc_trainer(),
).run()
