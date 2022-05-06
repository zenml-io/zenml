#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import pandas as pd
from deepchecks.core.suite import SuiteResult
from deepchecks.tabular import Dataset
from deepchecks.tabular.datasets.classification import iris
from deepchecks.tabular.suites import full_suite
from rich import print
from sklearn.base import ClassifierMixin
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

from zenml.integrations.constants import DEEPCHECKS, SKLEARN
from zenml.integrations.deepchecks.visualizers import DeepchecksVisualizer
from zenml.logger import get_logger
from zenml.pipelines import pipeline
from zenml.repository import Repository
from zenml.steps import Output, step

logger = get_logger(__name__)

LABEL_COL = "target"


@step
def data_loader() -> Output(
    reference_dataset=pd.DataFrame, comparison_dataset=pd.DataFrame
):
    """Load the iris dataset."""
    iris_df = iris.load_data(data_format="Dataframe", as_train_test=False)
    label_col = "target"
    df_train, df_test = train_test_split(
        iris_df, stratify=iris_df[label_col], random_state=0
    )
    return df_train, df_test


@step
def trainer(df_train: pd.DataFrame) -> ClassifierMixin:
    # Train Model
    rf_clf = RandomForestClassifier(random_state=0)
    rf_clf.fit(df_train.drop(LABEL_COL, axis=1), df_train[LABEL_COL])
    return rf_clf


@step
def data_validator(
    reference_dataset: pd.DataFrame,
    comparison_dataset: pd.DataFrame,
    model: ClassifierMixin,
) -> SuiteResult:
    """Validate data using deepchecks"""
    ds_train = Dataset(reference_dataset, label=LABEL_COL, cat_features=[])
    ds_test = Dataset(comparison_dataset, label=LABEL_COL, cat_features=[])
    suite = full_suite()
    return suite.run(train_dataset=ds_train, test_dataset=ds_test, model=model)


@step
def post_validation(result: SuiteResult) -> None:
    """Consumes the SuiteResult."""
    print(result)


@pipeline(enable_cache=False, required_integrations=[DEEPCHECKS, SKLEARN])
def data_validation_pipeline(
    data_loader,
    trainer,
    data_validator,
    post_validation,
):
    """Links all the steps together in a pipeline"""
    df_train, df_test = data_loader()
    model = trainer(df_train)
    validation_result = data_validator(
        reference_dataset=df_train,
        comparison_dataset=df_test,
        model=model,
    )
    post_validation(validation_result)


if __name__ == "__main__":
    pipeline = data_validation_pipeline(
        data_loader=data_loader(),
        trainer=trainer(),
        data_validator=data_validator(),
        post_validation=post_validation(),
    )
    pipeline.run()

    repo = Repository()
    pipeline = repo.get_pipeline(pipeline_name="data_validation_pipeline")
    last_run = pipeline.runs[-1]
    data_val_step = last_run.get_step(name="data_validator")
    DeepchecksVisualizer().visualize(data_val_step)
