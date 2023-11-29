# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2023. All rights reserved.
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


from zenml import get_step_context, step
from zenml.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


@step()
def save_model_to_deploy():
    """
    This step saves the latest model and tokenizer to the local filesystem.

    Note: It's recommended to use this step in a pipeline that is run locally,
    using the `local` orchestrator flavor because this step saves the model
    and tokenizer to the local filesystem that will later then be used by the deployment
    steps.

    Args:
        mlfow_model_name: The name of the model in MLFlow.
        stage: The stage of the model in MLFlow.
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    pipeline_extra = get_step_context().pipeline_run.config.extra
    logger.info(
        f" Loading latest version of the model for stage {pipeline_extra['target_env']}..."
    )
    # Get latest saved model version in target environment
    latest_version = get_step_context().model_version._get_model_version()

    # Load model and tokenizer from Model Control Plane
    model = latest_version.load_artifact(name="model")
    tokenizer = latest_version.load_artifact(name="tokenizer")
    # Save the model and tokenizer locally
    model_path = "./gradio/model"  # replace with the actual path
    tokenizer_path = "./gradio/tokenizer"  # replace with the actual path

    # Save model locally
    model.save_pretrained(model_path)
    tokenizer.save_pretrained(tokenizer_path)
    logger.info(
        f" Model and tokenizer saved to {model_path} and {tokenizer_path} respectively."
    )
    ### YOUR CODE ENDS HERE ###
