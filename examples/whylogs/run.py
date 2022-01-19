#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

import os
import pandas as pd

from sklearn import datasets
from whylogs import DatasetProfile

from zenml.integrations.whylogs.visualizers import WhylogsVisualizer
from zenml.integrations.whylogs.whylogs_utils import WhylogsContext
from zenml.integrations.whylogs.steps import (
    whylogs_profiler_step,
)

from zenml.core.repo import Repository
from zenml.logger import get_logger
from zenml.pipelines import pipeline
from zenml.steps import step, Output

logger = get_logger(__name__)

# Simply set these environment variables to point to a Whylabs account and all
# whylogs DatasetProfile artifacts that are produced by a pipeline run will
# also be uploaded to Whylabs.
#
# os.environ["WHYLABS_API_KEY"] = "YOUR-API-KEY"
# os.environ["WHYLABS_DEFAULT_ORG_ID"] = "YOUR-ORG-ID"

# NOTE: cache needs to be explicitly enabled for steps that take in step
# contexts
@step(enable_cache=True)
def data_loader(
    context: WhylogsContext,
) -> Output(data=pd.DataFrame, profile=DatasetProfile,):
    """Load the breast cancer dataset."""
    print("Loading data...")
    breast_cancer = datasets.load_breast_cancer()
    df = pd.DataFrame(
        data=breast_cancer.data, columns=breast_cancer.feature_names
    )
    df["class"] = pd.Categorical(
        pd.Series(breast_cancer.target).map(
            lambda x: breast_cancer.target_names[x]
        )
    )

    profile = context.log_dataframe(df, dataset_name="input_data")

    return df, profile


@step
def partial_split(
    input: pd.DataFrame,
) -> pd.DataFrame:
    """Returns a slice of the input dataset as a Pandas dataframe."""
    split = input[:100]
    return split


log_partial_data = whylogs_profiler_step(
    "partial_data_logger", dataset_name="partial"
)


@pipeline(enable_cache=True)
def data_split_pipeline(
    data_loader,
    partial_data,
    partial_data_logger,
):
    """Links all the steps together in a pipeline"""
    data, _ = data_loader()
    split = partial_data(data)
    partial_data_logger(split)


def visualize_statistics(step_name: str):
    repo = Repository()
    pipe = repo.get_pipelines()[-1]
    whylogs_outputs = pipe.runs[-1].get_step(name=step_name)
    WhylogsVisualizer().visualize(whylogs_outputs)



if __name__ == "__main__":

    pipeline = data_split_pipeline(
        data_loader=data_loader(),
        partial_data=partial_split(),
        partial_data_logger=log_partial_data,
    )

    pipeline.run()

    visualize_statistics("data_loader")
    visualize_statistics("partial_data_logger")
