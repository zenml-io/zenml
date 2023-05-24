#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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


import datetime
import os
from typing import List, Optional

from langchain.docstore.document import Document
from llama_index.readers.slack import SlackReader

from zenml.steps import BaseParameters, step


class SlackLoaderParameters(BaseParameters):
    """Params for Slack loader.

    Attributes:
        channel_ids: List of channel IDs to load.
        earliest_date: Earliest date to load.
        latest_date: Latest date to load.
    """

    channel_ids: List[str] = []
    earliest_date: Optional[datetime.datetime] = None
    latest_date: Optional[datetime.datetime] = None


@step(enable_cache=True)
def slack_loader(params: SlackLoaderParameters) -> List[Document]:
    """Langchain loader for Slack.

    Args:
        params: Parameters for the step.

    Returns:
        List of langchain documents.
    """
    loader = SlackReader(
        slack_token=os.environ["SLACK_BOT_TOKEN"],
        earliest_date=params.earliest_date,
        latest_date=params.latest_date,
    )
    documents = loader.load_data(channel_ids=params.channel_ids)
    return [d.to_langchain_format() for d in documents]
