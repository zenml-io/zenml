#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
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

from pipelines.training_pipeline.training_pipeline import (
    mlflow_example_pipeline,
)

from zenml.client import Client
from zenml.integrations.mlflow.mlflow_utils import get_tracking_uri

if __name__ == "__main__":
    mlflow_example_pipeline()

    print(
        "Now run \n "
        f"    mlflow ui --backend-store-uri '{get_tracking_uri()}'\n"
        "To inspect your experiment runs within the mlflow UI.\n"
        "You can find your runs tracked within the `mlflow_example_pipeline`"
        "experiment. Here you'll also be able to compare the two runs.)"
    )

    c = Client()
    orchestrator = c.active_stack.orchestrator
    orchestrator_config = orchestrator.config
    if orchestrator_config.get("kubeflow_hostname"):
        print("Kubeflow URL: `{orchestrator_config.kubeflow_hostname}`")
