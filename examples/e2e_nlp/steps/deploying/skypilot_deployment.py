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
import re

from zenml import step
from zenml.client import Client
from zenml.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


@step()
def deploy_to_skypilot():
    """
    This step deploy the model to a VM using SkyPilot.

    This step requires `skypilot` to be installed.
    as well as a configured cloud account locally (e.g. AWS, GCP, Azure).
    """
    import sky

    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    zenml_repo_root = Client().root
    if not zenml_repo_root:
        logger.warning(
            "You're running the `deploy_to_huggingface` step outside of a ZenML repo. "
            "Since the deployment step to huggingface is all about pushing the repo to huggingface, "
            "this step will only work within a ZenML repo where the gradio folder is present."
        )
        raise
    gradio_task_yaml = os.path.join(zenml_repo_root, "gradio", "serve.yaml")
    task = sky.Task.from_yaml(gradio_task_yaml)
    cluster_name = re.sub(r"[^a-zA-Z0-9]+", "-", "nlp_use_case-cluster")
    sky.launch(task, cluster_name=cluster_name, detach_setup=True)
    ### YOUR CODE ENDS HERE ###
