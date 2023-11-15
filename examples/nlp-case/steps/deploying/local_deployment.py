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

from typing import Optional, List
from typing_extensions import Annotated
import os
import subprocess

from zenml import step
from zenml.client import Client
from zenml.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


@step(enable_cache=False)
def deploy_locally(
    model_name_or_path: str,
    tokenizer_name_or_path: str,
    labels: List[str],
    title: Optional[str] = "ZenML NLP Use-Case",
    description: Optional[str] = "This is a demo of the ZenML NLP use-case using Gradio.",
    interpretation: Optional[str] = "default",
    example: Optional[str] = "This use-case is awesome!",
) -> Annotated[int, "process_id"]:
    """
    This step deploys the model locally by starting a Gradio app
    as a separate process in the background.

    Args:
        model_name_or_path: The name or path of the model to use.
        tokenizer_name_or_path: The name or path of the tokenizer to use.
        labels: The labels of the model.
        title: The title of the Gradio app.
        description: The description of the Gradio app.
        interpretation: The interpretation of the Gradio app.
        example: The example of the Gradio app.

    Returns:
        The process ID of the Gradio app.
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    def start_gradio_app(command: List[str]) -> int:
        """
        Start the Gradio app in a separate process.

        Args:
            command: The command to start the Gradio app.
        
        Returns:
            The process ID of the Gradio app.
        """
        # Start the Gradio app in a separate process
        process = subprocess.Popen(command)

        # Print the process ID
        logger.info(f"Started Gradio app with process ID: {process.pid}")

        return process.pid

    lables = ",".join(labels)
    # Construct the path to the app.py file
    zenml_repo_root = Client().root
    if not zenml_repo_root:
        raise RuntimeError(
            "You're running the `deploy_to_huggingface` step outside of a ZenML repo. "
            "Since the deployment step to huggingface is all about pushing the repo to huggingface, "
            "this step will not work outside of a ZenML repo where the gradio folder is present."
        )
    app_path = str(os.path.join(zenml_repo_root, "gradio", "app.py"))
    command = ["python", app_path, "--tokenizer_name_or_path", tokenizer_name_or_path, "--model_name_or_path", model_name_or_path, 
        "--labels", lables, "--title", title, "--description", description, 
       "--interpretation", interpretation, "--examples", example]
    logger.info(f"Command: {command}")
    # Call the function to launch the script
    pid = start_gradio_app(command)
    logger.info(f"Process ID: {pid}")
    logger.info(f"To kill the process, run: kill -9 {pid}")
    ### YOUR CODE ENDS HERE ###

    return pid