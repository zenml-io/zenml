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
"""Implementation of a step that sends an email alert."""

from typing import Optional

from zenml import get_step_context, step
from zenml.client import Client
from zenml.integrations.smtp_email.alerters.smtp_email_alerter import (
    SMTPEmailAlerterParameters,
    SMTPEmailAlerterPayload,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def smtp_email_alerter_post_step(
    message: str,
    recipient_email: Optional[str] = None,
    subject: Optional[str] = None,
    include_pipeline_info: bool = True,
) -> None:
    """Step that sends an email alert using the active alerter.

    DEPRECATED: Please use `alerter_post_step` instead. This step will be removed in a future release.

    Args:
        message: Message to be included in the email.
        recipient_email: Optional recipient email address. If not provided,
            the email will be sent to the default recipient configured
            in the alerter.
        subject: Optional custom subject for the email.
        include_pipeline_info: If True, includes pipeline and step information
            in the email.

    Raises:
        RuntimeError: If no alerter is configured in the active stack.
    """
    logger.warning(
        "DEPRECATION NOTICE: `smtp_email_alerter_post_step` is deprecated and will "
        "be removed in a future release. Please use `alerter_post_step` with "
        "an `AlerterMessage` object instead."
    )
    alerter = Client().active_stack.alerter
    if not alerter:
        raise RuntimeError(
            "No alerter configured in the active stack. "
            "Please configure an alerter in your stack."
        )

    # Create parameters for the email
    params = SMTPEmailAlerterParameters(
        recipient_email=recipient_email,
        subject=subject,
    )

    # Add pipeline info if requested
    if include_pipeline_info:
        context = get_step_context()
        params.payload = SMTPEmailAlerterPayload(
            pipeline_name=context.pipeline.name,
            step_name=context.step_run.name,
            stack_name=Client().active_stack.name,
        )

    # Send the email
    alerter.post(message=message, params=params)
