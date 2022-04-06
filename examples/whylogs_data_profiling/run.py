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

import pandas as pd
from sklearn import datasets
from sklearn.model_selection import train_test_split
from whylogs import DatasetProfile  # type: ignore

from zenml.integrations.constants import SKLEARN, WHYLOGS
from zenml.integrations.whylogs.steps import whylogs_profiler_step
from zenml.integrations.whylogs.visualizers import WhylogsVisualizer
from zenml.integrations.whylogs.whylogs_step_decorator import enable_whylogs
from zenml.logger import get_logger
from zenml.pipelines import pipeline
from zenml.repository import Repository
from zenml.steps import Output, step
from zenml.steps.step_context import StepContext

logger = get_logger(__name__)

# Simply set these environment variables to point to a Whylabs account and all
# whylogs DatasetProfile artifacts that are produced by a pipeline run will
# also be uploaded to Whylabs:
#
# import os
# os.environ["WHYLABS_API_KEY"] = "YOUR-API-KEY"
# os.environ["WHYLABS_DEFAULT_ORG_ID"] = "YOUR-ORG-ID"


# An existing zenml step can be easily extended to include whylogs profiling
# features by adding the @enable_whylogs decorator. The only prerequisite is
# that the step already include a step context parameter.
#
# Applying the @enable_whylogs decorator gives the user access to a `whylogs`
# step sub-context field which intermediates and facilitates the creation of
# whylogs DatasetProfile artifacts.
#
# The whylogs sub-context transparently incorporates ZenML specific
# information, such as project, pipeline name and specialized tags, into all
# dataset profiles that are generated with it. It also simplifies the whylogs
# profile generation process by abstracting away some of the whylogs specific
# details, such as whylogs session and logger initialization and management.
#
# NOTE: remember that cache needs to be explicitly enabled for steps that take
# in step contexts
@enable_whylogs
@step(enable_cache=True)
def data_loader(
    context: StepContext,
) -> Output(data=pd.DataFrame, profile=DatasetProfile,):
    """Load the diabetes dataset."""
    X, y = datasets.load_diabetes(return_X_y=True, as_frame=True)

    # merge X and y together
    df = pd.merge(X, y, left_index=True, right_index=True)

    # leverage the whylogs sub-context to generate a whylogs profile
    profile = context.whylogs.profile_dataframe(
        df, dataset_name="input_data", tags={"datasetId": "model-14"}
    )

    return df, profile


@step
def data_splitter(
    input: pd.DataFrame,
) -> Output(train=pd.DataFrame, test=pd.DataFrame,):
    """Splits the input dataset into train and test slices."""
    train, test = train_test_split(input, test_size=0.1, random_state=13)
    return train, test


# Another quick way of enhancing your pipeline with whylogs profiling features
# is with the `whylogs_profiler_step` function, which creates a step that runs
# whylogs data profiling on an input dataframe and returns the generated
# profile as an output artifact.
train_data_profiler = whylogs_profiler_step(
    "train_data_profiler", dataset_name="train", tags={"datasetId": "model-15"}
)
test_data_profiler = whylogs_profiler_step(
    "test_data_profiler", dataset_name="test", tags={"datasetId": "model-16"}
)


@pipeline(enable_cache=True, required_integrations=[SKLEARN, WHYLOGS])
def data_profiling_pipeline(
    data_loader,
    data_splitter,
    train_data_profiler,
    test_data_profiler,
):
    """Links all the steps together in a pipeline"""
    data, _ = data_loader()
    train, test = data_splitter(data)
    train_data_profiler(train)
    test_data_profiler(test)


def visualize_statistics(step_name: str):
    repo = Repository()
    pipe = repo.get_pipeline(pipeline_name="data_profiling_pipeline")
    whylogs_outputs = pipe.runs[-1].get_step(name=step_name)
    WhylogsVisualizer().visualize(whylogs_outputs)


if __name__ == "__main__":

    pipeline = data_profiling_pipeline(
        data_loader=data_loader(),
        data_splitter=data_splitter(),
        train_data_profiler=train_data_profiler,
        test_data_profiler=test_data_profiler,
    )

    pipeline.run()

    visualize_statistics("data_loader")
    visualize_statistics("train_data_profiler")
    visualize_statistics("test_data_profiler")
