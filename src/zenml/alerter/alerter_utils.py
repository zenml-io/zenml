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
"""Utility functions for alerters."""

from zenml.alerter.base_alerter import BaseAlerter
from zenml.exceptions import DoesNotExistException
from zenml.steps import StepContext


def get_active_alerter(context: StepContext) -> BaseAlerter:
    """Get the alerter component of the active stack.

    Args:
        context: StepContext of the ZenML repository.

    Returns:
        Alerter component of the active stack.

    Raises:
        DoesNotExistException: if active stack has no slack alerter.
    """
    # TODO: duplicate code with examples/feast_feature_store/run.py
    if not context.stack:
        raise DoesNotExistException(
            "No active stack is available. "
            "Please make sure that you have registered and set a stack."
        )
    if not context.stack.alerter:
        raise DoesNotExistException(
            "The active stack needs to have an alerter component registered "
            "to be able to use an `alerter_step`. "
            "You can create a new stack with e.g. a Slack alerter component or update "
            "your existing stack to add this component, e.g.:\n\n"
            "  'zenml alerter register slack_alerter --flavor=slack' ...\n"
            "  'zenml stack register stack-name -al slack_alerter ...'\n"
        )
    return context.stack.alerter
