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

from typing import ClassVar, Optional

from zenml.alerter.base_alerter import BaseAlerter
from zenml.integrations.slack import SLACK_ALERTER_FLAVOR
from zenml.logger import get_logger

logger = get_logger(__name__)


class SlackAlerter(BaseAlerter):
    """TBD

    ```python
    from zenml.steps import StepContext

    @enable_wandb
    @step
    def my_step(context: StepContext, ...)
        context.stack.experiment_tracker  # get the tracking_uri etc. from here
    ```

    Attributes:
        entity: Name of an existing wandb entity.
        project_name: Name of an existing wandb project to log to.
        api_key: API key to should be authorized to log to the configured wandb
            entity and project.
    """

    slack_token: str
    slack_channel_id: str
    thread_ts: Optional[str] = None

    # Class Configuration
    FLAVOR: ClassVar[str] = SLACK_ALERTER_FLAVOR
