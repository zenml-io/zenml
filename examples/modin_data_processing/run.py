import modin.pandas as pd
from sklearn.base import ClassifierMixin
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC

from zenml.pipelines import pipeline
from zenml.steps import Output, step


@step
def simple_data_splitter() -> Output(
    train_set=pd.DataFrame, test_set=pd.DataFrame
):
    # Load the wine dataset
    # dataset = load_wine(as_frame=True).frame
    
    dataset = pd.read_csv("2020_Yellow_Taxi_Trip_Data_Chunk.csv")
    print(dataset.dtypes)
    print(dataset.head())
    print(dataset.columns)
    dataset = dataset.drop(columns=["tpep_pickup_datetime" , "tpep_dropoff_datetime", "store_and_fwd_flag"])
    dataset = dataset.fillna(0)
    # Split the dataset into training and dev subsets
    train_set, test_set = train_test_split(
        dataset,
    )
    return train_set, test_set


@step
def simple_svc_trainer(
    train_set: pd.DataFrame,
    test_set: pd.DataFrame,
) -> ClassifierMixin:
    """Trains a sklearn SVC classifier."""
    X_train, y_train = train_set.drop("passenger_count", axis=1), train_set["passenger_count"]
    X_test, y_test = test_set.drop("passenger_count", axis=1), test_set["passenger_count"]
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
