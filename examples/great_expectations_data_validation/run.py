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

from pipelines.validation import validation_pipeline

from zenml.client import Client
from zenml.enums import StoreType
from zenml.logger import get_logger
from zenml.post_execution import get_pipeline

logger = get_logger(__name__)

if __name__ == "__main__":
    validation_pipeline()

    p = get_pipeline("validation_pipeline")
    run_metadata = p.runs[0].metadata
    orchestrator_url = run_metadata.get("orchestrator_url")

    client = Client()

    if client.zen_store.type == StoreType.REST:
        url = client.zen_store.url
        url = (
            url
            + f"/workspaces/{client.active_workspace.name}/all-runs/{str(p.runs[0].id)}/dag"
        )
        logger.info(
            f"\n\n****Check out the ZenML dashboard to see your run:****\n{url}"
        )

    if orchestrator_url:
        logger.info(
            f"\n\n****See your run directly in the orchestrator:****\n{orchestrator_url}"
        )
