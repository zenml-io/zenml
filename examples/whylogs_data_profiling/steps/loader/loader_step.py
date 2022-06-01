#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
import pandas as pd
from sklearn import datasets
from whylogs import DatasetProfile

from zenml.integrations.whylogs.whylogs_step_decorator import enable_whylogs
from zenml.steps import step, Output, StepContext


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
