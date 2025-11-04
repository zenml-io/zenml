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
"""Utilities to access the active Trackio run from pipeline steps."""

from typing import Any

from zenml.client import Client


def get_trackio_run() -> Any:
    """Return the Trackio run associated with the currently executing step.

    Returns:
        The Trackio run instance created for the active step.

    Raises:
        RuntimeError: If the active stack does not contain a Trackio experiment
            tracker or the tracker has not yet been initialized.
    """

    from zenml.integrations.trackio.experiment_trackers import (
        TrackioExperimentTracker,
    )

    experiment_tracker = Client().active_stack.experiment_tracker

    if experiment_tracker is None:
        raise RuntimeError(
            "Unable to access a Trackio run: No experiment tracker is "
            "configured for the active stack."
        )

    if not isinstance(experiment_tracker, TrackioExperimentTracker):
        raise RuntimeError(
            "Unable to access a Trackio run: The experiment tracker in the "
            "active stack is not the Trackio integration."
        )

    try:
        return experiment_tracker.active_run
    except RuntimeError as exc:
        raise RuntimeError(
            "Unable to access a Trackio run: The tracker was not initialized. "
            "Ensure that the step enabling the experiment tracker is running "
            "when calling this helper."
        ) from exc
