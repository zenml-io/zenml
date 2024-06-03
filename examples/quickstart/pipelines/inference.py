# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2024. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from steps import (
    data_loader,
    inference_predict,
    inference_preprocessor,
)

from zenml import get_pipeline_context, pipeline
from zenml.logger import get_logger

logger = get_logger(__name__)


@pipeline
def inference(random_state: int, target: str):
    """
    Model inference pipeline.

    This is a pipeline that loads the inference data, processes it with
    the same preprocessing pipeline used in training, and runs inference
    with the trained model.

    Args:
        random_state: Random state for reproducibility.
        target: Name of target column in dataset.
    """
    # Get the production model artifact
    model = get_pipeline_context().model.get_artifact("sklearn_classifier")

    # Get the preprocess pipeline artifact associated with this version
    preprocess_pipeline = get_pipeline_context().model.get_artifact(
        "preprocess_pipeline"
    )

    # Link all the steps together by calling them and passing the output
    #  of one step as the input of the next step.
    df_inference = data_loader(random_state=random_state, is_inference=True)
    df_inference = inference_preprocessor(
        dataset_inf=df_inference,
        preprocess_pipeline=preprocess_pipeline,
        target=target,
    )
    inference_predict(
        model=model,
        dataset_inf=df_inference,
    )
