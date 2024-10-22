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
from types import TracebackType
from typing import Any, Dict, Optional, Tuple, Type
from unittest.mock import patch
from uuid import UUID

from pytest_mock import MockFixture

from zenml.analytics.enums import AnalyticsEvent
from zenml.enums import StackComponentType, StoreType


def event_check(
    _,
    user_id: UUID,
    event: AnalyticsEvent,
    properties: Optional[Dict[Any, Any]],
) -> Tuple[bool, str]:
    """Mock function to replace the 'zenml.analytics.track' function for tests.

    By utilizing this mock function, we can validate the inputs given to
    actual track function.

    Args:
        user_id: the string representation of the client id
        event: the type of the event
        properties: the collection of metadata describing the event

    Returns:
        Tuple (success flag, the original message).
    """
    # Check whether the user id corresponds to the client id
    from zenml.client import Client
    from zenml.config.global_config import GlobalConfiguration

    gc = GlobalConfiguration()
    client = Client()

    # Check the validity of the event
    assert event in AnalyticsEvent.__members__.values()

    # Check whether common parameters are included in the metadata
    assert "environment" in properties
    assert "python_version" in properties
    assert "version" in properties
    assert "client_id" in properties
    assert "user_id" in properties
    assert "server_id" in properties
    assert "deployment_type" in properties
    assert "database_type" in properties

    assert user_id == client.active_user.id

    assert properties["user_id"] == str(client.active_user.id)
    assert properties["client_id"] == str(gc.user_id)

    if event == AnalyticsEvent.REGISTERED_STACK:
        assert "entity_id" in properties

        assert StackComponentType.ARTIFACT_STORE in properties
        assert StackComponentType.ORCHESTRATOR in properties

    if event == AnalyticsEvent.REGISTERED_STACK_COMPONENT:
        assert "type" in properties
        assert properties["type"] in StackComponentType.__members__.values()

        assert "flavor" in properties
        assert "entity_id" in properties

    if event == AnalyticsEvent.RUN_PIPELINE:
        assert "store_type" in properties
        assert properties["store_type"] in StoreType.__members__.values()

        assert "artifact_store" in properties
        assert (
            properties["artifact_store"]
            == client.active_stack_model.components[
                StackComponentType.ARTIFACT_STORE
            ][0].flavor_name
        )

        assert "orchestrator" in properties
        assert (
            properties["orchestrator"]
            == client.active_stack_model.components[
                StackComponentType.ORCHESTRATOR
            ][0].flavor_name
        )

    return True, ""


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
    behavior, so we can catch the errors which happen during this process.
    """


@patch.dict(
    "os.environ", {"ZENML_DEBUG": "true", "ZENML_ANALYTICS_OPT_IN": "true"}
)
def test_analytics_event(
    mocker: MockFixture, clean_client, one_step_pipeline, empty_step
) -> None:
    """Checks whether the event sent for analytics has the right properties.

    This is achieved by modifying the behavior of several functionalities
    within the analytics process:

        1 - The environmental variables are patched to set the "ZENML_DEBUG"
            and "ZENML_ANALYTICS_OPT_IN" to true. This way, the process to send
            analytics events is activated. ("ZENML_DEBUG" is only set as a
            security measure.)
        2 - The function "analytics.client.Client.track" which is responsible
            for sending the actual analytics events is also patched with a
            different function. This way, we stop sending any actual events
            during the test and have a platform to check the validity of
            the final attributes which get passed to it.
        3 - Finally, the exit function of our AnalyticsContext is also
            patched. In a normal workflow, this context manager is responsible
            for keeping the main thread alive by suppressing any exceptions
            which might happen during the preparation/tracking of any events.
            However, since we want to test the attributes, this method needs to
            be disabled with a dummy method, so that we can catch any errors
            that happen during the check.

    Once the patches are set, we can execute any events such as `initializing
    zenml`, `registering stacks` or `registering stack components` and check
    the validity of the corresponding event and metadata.
    """
    # Mocking analytics version 2
    mocker.patch("zenml.analytics.client.Client.track", new=event_check)

    mocker.patch(
        "zenml.analytics.context.AnalyticsContext.__exit__",
        new=event_context_exit,
    )

    # Test zenml initialization
    clean_client.initialize()

    # Test stack and component registration
    clean_client.create_stack_component(
        name="new_artifact_store",
        flavor="local",
        component_type=StackComponentType.ARTIFACT_STORE,
        configuration={"path": "/tmp/path/for/test"},  # nosec
    )
    clean_client.create_stack(
        name="new_stack",
        components={
            StackComponentType.ARTIFACT_STORE: "new_artifact_store",
            StackComponentType.ORCHESTRATOR: "default",
        },
    )

    # Test pipeline run
    one_step_pipeline(empty_step).with_options(unlisted=True)()
