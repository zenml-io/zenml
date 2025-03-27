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

from steps import notify_on_failure, notify_on_success, model_deployer

from zenml import pipeline
from zenml.client import Client


@pipeline(on_failure=notify_on_failure)
def e2e_use_case_deployment():
    """
    Model deployment pipeline.

    This is a pipeline deploys trained model for future inference.
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    # Link all the steps together by calling them and passing the output
    # of one step as the input of the next step.
    ########## Deployment stage ##########
    client = Client()
    # Fetch by name alone - uses the latest version of this artifact
    artifact = client.get_artifact_version(name_id_or_prefix="model_registry_uri")
    model_registry_uri = artifact.load()
    model_deployer(
        model_registry_uri=model_registry_uri,
    )

    notify_on_success(after=["model_deployer"])
    ### YOUR CODE ENDS HERE ###
