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

from pipelines import inference_pipeline
from rich import print

from zenml.integrations.mlflow.mlflow_utils import get_tracking_uri


def main():
    # initialize and run the training pipeline
    # training_pipeline()

    # initialize and run the inference pipeline
    inference_pipeline()

    print(
        "You can run:\n "
        "[italic green]    mlflow ui --backend-store-uri "
        f"'{get_tracking_uri()}'[/italic green]\n "
        "...to inspect your experiment runs and models "
        "within the MLflow UI.\nYou can find your runs tracked within the "
        "`training_pipeline` experiment. There you'll also be able to "
        "compare two or more runs and view the registered models.\n\n"
    )


if __name__ == "__main__":
    main()
