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

from rich.console import Console

from zenml import get_step_context
from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)


def alerter_failure_hook(exception: BaseException) -> None:
    """Standard failure hook that executes after step fails.

    This hook uses any `BaseAlerter` that is configured within the active stack to post a message.

    Args:
        exception: Original exception that lead to step failing.
    """
    context = get_step_context()
    alerter = Client().active_stack.alerter
    if alerter:
        output_captured = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = output_captured
        console = Console()
        console.print_exception(show_locals=False)

        sys.stdout = original_stdout
        rich_traceback = output_captured.getvalue()

        message = "*Failure Hook Notification! Step failed!*" + "\n\n"
        message += f"Pipeline name: `{context.pipeline.name}`" + "\n"
        message += f"Run name: `{context.pipeline_run.name}`" + "\n"
        message += f"Step name: `{context.step_run.name}`" + "\n"
        message += f"Parameters: `{context.step_run.config.parameters}`" + "\n"
        message += (
            f"Exception: `({type(exception)}) {rich_traceback}`" + "\n\n"
        )
        alerter.post(message)
    else:
        logger.warning(
            "Specified standard failure hook but no alerter configured in the stack. Skipping.."
        )


def alerter_success_hook() -> None:
    """Standard success hook that executes after step finishes successfully.

    This hook uses any `BaseAlerter` that is configured within the active stack to post a message.
    """
    context = get_step_context()
    alerter = Client().active_stack.alerter
    if alerter:
        message = (
            "*Success Hook Notification! Step completed successfully*" + "\n\n"
        )
        message += f"Pipeline name: `{context.pipeline.name}`" + "\n"
        message += f"Run name: `{context.pipeline_run.name}`" + "\n"
        message += f"Step name: `{context.step_run.name}`" + "\n"
        message += f"Parameters: `{context.step_run.config.parameters}`" + "\n"
        alerter.post(message)
    else:
        logger.warning(
            "Specified standard success hook but no alerter configured in the stack. Skipping.."
        )
