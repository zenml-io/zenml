#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
import os
from contextlib import ExitStack as does_not_raise
from types import TracebackType
from typing import Any, Dict, Optional, Type
from uuid import UUID

from pytest_mock import MockFixture

from zenml.config.global_config import GlobalConfiguration
from zenml.enums import StackComponentType
from zenml.utils.analytics_utils import (
    AnalyticsEvent,
    get_segment_key,
    track_event,
)


class environment_handler(object):
    """Context manager to manipulate the environment variables during a process."""

    def __init__(self, params: Optional[Dict[str, str]] = None):
        """Initialization of the manager.

         It saves the provided additional params.

        Args:
            params: The type of the analytics event
        """
        self.original_environment = None
        self.params = params or {}

    def __enter__(self) -> "environment_handler":
        """Enter function of the manager.

        It creates a copy of the original set of environment variables and
        updates it with the provided params.

        Returns:
            the handler instance.
        """
        self.original_environment = os.environ.copy()
        os.environ.update(self.params)

        return self

    def __exit__(
        self,
        type_: Optional[Any],
        value: Optional[Any],
        traceback: Optional[Any],
    ) -> Any:
        """Exit function of the manager.

        Reverts the environmental variables back to their original state.

        Args:
            type_: The class of the exception
            value: The instance of the exception
            traceback: The traceback of the exception

        """
        os.environ = self.original_environment


def event_check(
    user_id: str, event: AnalyticsEvent, metadata: Dict[str, str]
) -> None:
    """Mock function to replace the 'analytics.track' function for tests.

    By utilizing this mock function, we can validate the inputs given to
    actual track function.

    Args:
        user_id: the string representation of the client id
        event: the type of the event
        metadata: the collection of metadata describing the event

    Raises:
        ...
    """
    # Check whether the user id corresponds to the client id
    gc = GlobalConfiguration()
    assert user_id == str(gc.user_id)

    # Check the validity of the event
    assert event in AnalyticsEvent.__members__.values()

    # Check the type of each metadata entry
    assert all([not isinstance(v, UUID) for v in metadata.values()])

    # Check whether common parameters are included in the metadata
    assert "environment" in metadata
    assert "python_version" in metadata
    assert "version" in metadata
    assert "event_success" in metadata

    if event == AnalyticsEvent.REGISTERED_STACK:
        assert StackComponentType.ARTIFACT_STORE in metadata
        assert StackComponentType.ORCHESTRATOR in metadata

        assert "project_id" in metadata
        assert "entity_id" in metadata
        assert "user_id" in metadata
        assert "is_shared" in metadata

    if event == AnalyticsEvent.REGISTERED_STACK_COMPONENT:
        assert "type" in metadata
        assert "flavor" in metadata
        assert "entity_id" in metadata
        assert "user_id" in metadata
        assert "is_shared" in metadata

    if event == AnalyticsEvent.RUN_PIPELINE:
        assert "store_type" in metadata
        assert "artifact_store" in metadata
        assert "orchestrator" in metadata


def event_context_exit(
    _,
    exc_type: Optional[Type[BaseException]],
    exc_val: Optional[BaseException],
    exc_tb: Optional[TracebackType],
):
    """Mock exit function to replace the exit method of the AnalyticsContext.

    Normally, the analytics context has an exit function which allows the main
    thread to continue by suppressing exceptions which occur during the event
    tracking. However, for the sake of the tests we would like to disable this
    behaviour, so we can catch the errors which happen during this process.
    """


def test_analytics_event(
    mocker: MockFixture, clean_client, one_step_pipeline, empty_step
) -> None:
    with environment_handler(
        params={"ZENML_DEBUG": "true", "ZENML_ANALYTICS_OPT_IN": "true"}
    ):
        mocker.patch("analytics.track", new=event_check)
        mocker.patch(
            "zenml.utils.analytics_utils.AnalyticsContext.__exit__",
            new=event_context_exit,
        )

        # Test zenml initialization
        clean_client.initialize()

        # Test stack and component registration
        clean_client.create_stack_component(
            name="new_artifact_store",
            flavor="local",
            component_type=StackComponentType.ARTIFACT_STORE,
            configuration={"path": "/tmp/path/for/test"},
        )
        clean_client.create_stack(
            name="new_stack",
            components={
                StackComponentType.ARTIFACT_STORE: "new_artifact_store",
                StackComponentType.ORCHESTRATOR: "default",
            },
        )

        # Test pipeline run
        one_step_pipeline(empty_step()).run(unlisted=True)


def test_get_segment_key():
    """Checks the get_segment_key method returns a value"""
    with does_not_raise():
        get_segment_key()


def test_track_event_conditions():
    """It should return true for the analytics events but false for everything
    else."""
    assert track_event(AnalyticsEvent.OPT_IN_ANALYTICS)
    assert track_event(AnalyticsEvent.OPT_OUT_ANALYTICS)
    assert not track_event(AnalyticsEvent.EVENT_TEST)
