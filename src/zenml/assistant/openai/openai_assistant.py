#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Example file of what an action Plugin could look like."""

import os
from abc import ABC, abstractmethod
from typing import ClassVar, Type

from zenml.assistant.base_assistant import (
    BaseAssistantFlavor,
    BaseAssistantHandler,
)
from zenml.logger import get_logger
from zenml.models.v2.core.assistant import AssistantRequest, AssistantResponse

logger = get_logger(__name__)


class OpenAIAssistantHandler(BaseAssistantHandler, ABC):
    """Example assistant handler."""

    def __init__(self):
        """Initialize the OpenAI Assistant Handler."""
        super().__init__()
        if not os.getenv("OPENAI_API_KEY"):
            RuntimeError(
                "Please set the openai key in your env `export OPENAI_AI_KEY=xxxxxxxxxxxxxxx`"
            )

    @abstractmethod
    def make_assistant_call(
        self, assistant_request: AssistantRequest
    ) -> AssistantResponse:
        """Make call to assistant backend.

        Args:
            assistant_request: Request to forward to the backend.

        Returns:
            The response from the backend.
        """


# -------------------- Pipeline Run Flavor -----------------------------------


class OpenAIAssistantFlavor(BaseAssistantFlavor):
    """Enables users to discover assistant handlers."""

    FLAVOR: ClassVar[str] = "openai"
    PLUGIN_CLASS: ClassVar[Type[OpenAIAssistantHandler]] = (
        OpenAIAssistantHandler
    )
