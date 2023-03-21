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
"""Functionality for standard hooks."""

import io
import sys
from typing import TYPE_CHECKING

import openai
from rich.console import Console

from zenml.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.steps import BaseParameters, StepContext


def openai_alerter_failure_hook(
    context: "StepContext", params: "BaseParameters", exception: BaseException
) -> None:
    """Failure hook that executes after step fails, with OpenAI GPT support.

    This hook uses OpenAI's LLM to generate suggestions on how to fix a step
    that fails.

    Args:
        context: Context of the step.
        params: Parameters used in the step.
        exception: Original exception that lead to step failing.
    """
    if context.stack and context.stack.alerter:
        output_captured = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = output_captured
        console = Console()
        console.print_exception(show_locals=True)

        sys.stdout = original_stdout
        rich_traceback = output_captured.getvalue()

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "user",
                    "content": f"This is an error message (following an exception of type '{type(exception)}') I encountered while executing a ZenML step. Please suggest ways I might fix the problem. Feel free to give code snippets as examples, and note that your response will be piped to a Slack bot so make sure the formatting is appropriate: {exception} -- {rich_traceback}. Thank you!",
                }
            ],
        )
        suggestion = response["choices"][0]["message"]["content"]
        context.stack.alerter.post(suggestion)
    else:
        logger.warning(
            "Specified standard failure hook but no alerter configured in the stack. Skipping.."
        )
