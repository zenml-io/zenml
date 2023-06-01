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
from zenml.constants import (
    METADATA_EXPERIMENT_TRACKER_URL,
    METADATA_ORCHESTRATOR_URL,
)
from zenml.enums import StoreType
from zenml.logger import get_logger

logger = get_logger(__name__)


if __name__ == "__main__":
    mlflow_example_pipeline()

    trainer_step = mlflow_example_pipeline.get_runs()[0].get_step("tf_trainer")
    tracking_url = trainer_step.metadata.get(
        METADATA_EXPERIMENT_TRACKER_URL
    ).value
    orchestrator_url = trainer_step.get(METADATA_ORCHESTRATOR_URL).value

    client = Client()

    if client.zen_store.type == StoreType.REST:
        url = client.zen_store.url
        url = (
            url
            + f"/workspaces/{client.active_workspace.name}/all-runs/{str(trainer_step.runs[0].id)}/dag"
        )
        logger.info(
            f"\n\n****Check out the ZenML dashboard to see your run:****\n{url}"
        )

    if orchestrator_url:
        logger.info(
            f"\n\n****See your run directly in the orchestrator:****\n{orchestrator_url}"
        )

    if tracking_url:
        logger.info(
            f"\n\n****See your run directly in the experiment tracker:****\n"
        )
        logger.info(
            "Now run \n "
            f"    mlflow ui --backend-store-uri '{tracking_url}'\n"
            "To inspect your experiment runs within the mlflow UI.\n"
            "You can find your runs tracked within the `mlflow_example_pipeline` "
            "experiment."
        )
