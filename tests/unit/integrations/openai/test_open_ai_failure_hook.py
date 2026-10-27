#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Tests for the OpenAI alerter failure hooks."""

from unittest.mock import MagicMock, patch

import pytest

from zenml.integrations.openai.hooks import open_ai_failure_hook
from zenml.integrations.openai.hooks.open_ai_failure_hook import (
    openai_chatgpt_alerter_failure_hook,
    openai_gpt4_alerter_failure_hook,
)


@pytest.mark.parametrize(
    "hook, expected_model",
    [
        (openai_chatgpt_alerter_failure_hook, "gpt-5.6-terra"),
        (openai_gpt4_alerter_failure_hook, "gpt-4o"),
    ],
)
def test_alerter_hook_asks_the_expected_model(hook, expected_model):
    """The hooks send their suggestion request to the expected model."""
    client = MagicMock()
    client.get_secret.return_value.secret_values = {"api_key": "sk-test"}
    openai_client = MagicMock()
    openai_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content="try again"))
    ]

    with (
        patch.object(open_ai_failure_hook, "Client", return_value=client),
        patch.object(open_ai_failure_hook, "get_step_context"),
        patch.object(
            open_ai_failure_hook, "OpenAI", return_value=openai_client
        ),
    ):
        try:
            raise ValueError("boom")
        except ValueError as e:
            # the hook prints the active traceback, as it does when a step fails
            hook(e)

    create = openai_client.chat.completions.create
    create.assert_called_once()
    assert create.call_args.kwargs["model"] == expected_model
    client.active_stack.alerter.post.assert_called_once()
