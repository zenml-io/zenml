# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2025. All rights reserved.
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

from typing import List, Optional

from steps import (
    data_loader,
    inference_predict,
    inference_preprocessor,
)

from zenml import get_pipeline_context, pipeline
from zenml.logger import get_logger
from zenml.steps import get_step_context

logger = get_logger(__name__)

# Import the init hook
from hooks import init_hook


@pipeline(
    enable_cache=False,
    on_init=init_hook,
)
def inference(
    random_state: int,
    target: str,
    input_data: Optional[List[List[float]]] = None,
):
    """
    Model inference pipeline.

    This pipeline can either load inference data from sklearn or accept
    input data directly for serving. It processes the data with the same
    preprocessing pipeline used in training and runs inference with the
    trained model.

    Args:
        random_state: Random state for reproducibility when loading from sklearn.
        target: Name of target column in dataset.
        input_data: Optional input data as list of feature vectors. If provided,
            this data will be used instead of loading from sklearn.
    """
    # Try to get preloaded model from pipeline state first
    step_context = get_step_context()
    pipeline_state = step_context.pipeline_state if step_context else None

    if (
        pipeline_state
        and hasattr(pipeline_state, "model")
        and pipeline_state.model
    ):
        # Use preloaded model from pipeline state (serving mode)
        model = pipeline_state.model
        preprocess_pipeline = pipeline_state.preprocessor
        logger.info("Using preloaded model from pipeline state")
    else:
        # Fallback to loading artifacts (batch mode)
        model = get_pipeline_context().model.get_artifact("sklearn_classifier")
        preprocess_pipeline = get_pipeline_context().model.get_artifact(
            "preprocess_pipeline"
        )
        logger.info("Loading model artifacts from ZenML store")

    # Link all the steps together by calling them and passing the output
    #  of one step as the input of the next step.
    df_inference = data_loader(
        random_state=random_state, is_inference=True, input_data=input_data
    )
    df_inference = inference_preprocessor(
        dataset_inf=df_inference,
        preprocess_pipeline=preprocess_pipeline,
        target=target,
    )
    predictions = inference_predict(
        model=model,
        dataset_inf=df_inference,
    )
    return predictions
