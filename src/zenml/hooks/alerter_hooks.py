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

import traceback
from typing import TYPE_CHECKING

from zenml import get_step_context
from zenml.client import Client
from zenml.logger import get_logger

if TYPE_CHECKING:
    pass

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
        # Use standard Python traceback instead of Rich traceback
        tb_lines = traceback.format_exception(
            type(exception), exception, exception.__traceback__
        )
        plain_traceback = "".join(tb_lines).strip()

        # Try to use AlerterMessage for better structured alerts
        try:
            from zenml.models.v2.misc.alerter_models import AlerterMessage

            message = AlerterMessage(
                title="Pipeline Failure Alert",
                body=(
                    f"Step: {context.step_run.name}\n"
                    f"Pipeline: {context.pipeline.name}\n"
                    f"Run: {context.pipeline_run.name}\n"
                    f"Parameters: {context.step_run.config.parameters}\n"
                    f"Exception: ({type(exception).__name__}) {str(exception)}\n\n"
                    f"{plain_traceback}"
                ),
                metadata={
                    "pipeline_name": context.pipeline.name,
                    "run_name": context.pipeline_run.name,
                    "step_name": context.step_run.name,
                    "exception_type": type(exception).__name__,
                    "stack_name": Client().active_stack.name,
                },
            )
            alerter.post(message)
        except Exception as e:
            # Fall back to string format for backwards compatibility
            logger.debug(
                f"Falling back to string format for alerter hook. "
                f"Consider updating your alerter to support AlerterMessage. Error: {e}"
            )
            fallback_message = (
                "*Failure Hook Notification! Step failed!*" + "\n\n"
            )
            fallback_message += (
                f"Pipeline name: `{context.pipeline.name}`" + "\n"
            )
            fallback_message += (
                f"Run name: `{context.pipeline_run.name}`" + "\n"
            )
            fallback_message += f"Step name: `{context.step_run.name}`" + "\n"
            fallback_message += (
                f"Parameters: `{context.step_run.config.parameters}`" + "\n"
            )
            fallback_message += (
                f"Exception: `({type(exception).__name__}) {str(exception)}`"
                + "\n\n"
            )
            fallback_message += f"{plain_traceback}"
            alerter.post(fallback_message)
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
        # Try to use AlerterMessage for better structured alerts
        try:
            from zenml.models.v2.misc.alerter_models import AlerterMessage

            message = AlerterMessage(
                title="Pipeline Success Notification",
                body=(
                    f"Step: {context.step_run.name}\n"
                    f"Pipeline: {context.pipeline.name}\n"
                    f"Run: {context.pipeline_run.name}\n"
                    f"Parameters: {context.step_run.config.parameters}"
                ),
                metadata={
                    "pipeline_name": context.pipeline.name,
                    "run_name": context.pipeline_run.name,
                    "step_name": context.step_run.name,
                    "stack_name": Client().active_stack.name,
                    "status": "success",
                },
            )
            alerter.post(message)
        except Exception as e:
            # Fall back to string format for backwards compatibility
            logger.debug(
                f"Falling back to string format for alerter hook. "
                f"Consider updating your alerter to support AlerterMessage. Error: {e}"
            )
            fallback_message = (
                "*Success Hook Notification! Step completed successfully*"
                + "\n\n"
            )
            fallback_message += (
                f"Pipeline name: `{context.pipeline.name}`" + "\n"
            )
            fallback_message += (
                f"Run name: `{context.pipeline_run.name}`" + "\n"
            )
            fallback_message += f"Step name: `{context.step_run.name}`" + "\n"
            fallback_message += (
                f"Parameters: `{context.step_run.config.parameters}`" + "\n"
            )
            alerter.post(fallback_message)
    else:
        logger.warning(
            "Specified standard success hook but no alerter configured in the stack. Skipping.."
        )
