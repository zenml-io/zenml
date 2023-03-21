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

import openai
from rich.console import Console

from zenml.logger import get_logger
from zenml.steps import BaseParameters, StepContext

logger = get_logger(__name__)


def openai_alerter_failure_hook_helper(
    context: StepContext,
    params: BaseParameters,
    exception: BaseException,
    model_name: str,
) -> None:
    if context.stack and context.stack.alerter:
        output_captured = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = output_captured
        console = Console()
        console.print_exception(show_locals=False)

        sys.stdout = original_stdout
        rich_traceback = output_captured.getvalue()

        response = openai.ChatCompletion.create(  # type: ignore[no-untyped-call]
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": f"This is an error message (following an exception of type '{type(exception)}') I encountered while executing a ZenML step. Please suggest ways I might fix the problem. Feel free to give code snippets as examples, and note that your response will be piped to a Slack bot so make sure the formatting is appropriate: {exception} -- {rich_traceback}. Thank you!",
                }
            ],
        )
        suggestion = response["choices"][0]["message"]["content"]
        message = "*Failure Hook Notification! Step failed!*" + "\n\n"
        message += f"Pipeline name: `{context.pipeline_name}`" + "\n"
        message += f"Run name: `{context.run_name}`" + "\n"
        message += f"Step name: `{context.step_name}`" + "\n"
        message += f"Parameters: `{params}`" + "\n"
        message += f"Exception: `({type(exception)}) {exception}`" + "\n\n"
        message += (
            f"Step Cache Enabled: `{'True' if context.cache_enabled else 'False'}`"
            + "\n\n"
        )
        message += (
            f"*OpenAI ChatGPT's suggestion on how to fix it:*\n `{suggestion}`"
            + "\n"
        )
        context.stack.alerter.post(message)
    else:
        logger.warning(
            "Specified standard failure hook but no alerter configured in the stack. Skipping.."
        )


def openai_chatgpt_alerter_failure_hook(
    context: StepContext,
    params: BaseParameters,
    exception: BaseException,
) -> None:
    openai_alerter_failure_hook_helper(
        context, params, exception, "gpt-3.5-turbo"
    )


def openai_gpt4_alerter_failure_hook(
    context: StepContext,
    params: BaseParameters,
    exception: BaseException,
) -> None:
    openai_alerter_failure_hook_helper(context, params, exception, "gpt-4")
