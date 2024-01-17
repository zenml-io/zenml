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

import os

from huggingface_hub import HfApi

from zenml import step
from zenml.client import Client
from zenml.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


@step()
def deploy_to_huggingface(
    repo_name: str,
):
    """
    This step deploy the model to huggingface.

    Args:
        repo_name: The name of the repo to create/use on huggingface.
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    secret = Client().get_secret("huggingface_creds")
    assert secret, "No secret found with name 'huggingface_creds'. Please create one that includes your `username` and `token`."
    token = secret.secret_values["token"]
    api = HfApi(token=token)
    hf_repo = api.create_repo(
        repo_id=repo_name, repo_type="space", space_sdk="gradio", exist_ok=True
    )
    zenml_repo_root = Client().root
    if not zenml_repo_root:
        logger.warning(
            "You're running the `deploy_to_huggingface` step outside of a ZenML repo. "
            "Since the deployment step to huggingface is all about pushing the repo to huggingface, "
            "this step will not work outside of a ZenML repo where the gradio folder is present."
        )
        raise
    gradio_folder_path = os.path.join(zenml_repo_root, "gradio")
    space = api.upload_folder(
        folder_path=gradio_folder_path,
        repo_id=hf_repo.repo_id,
        repo_type="space",
    )
    logger.info(f"Space created: {space}")
    ### YOUR CODE ENDS HERE ###
