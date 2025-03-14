#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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


from typing import Any, Optional
from uuid import UUID

from typing_extensions import Annotated

from zenml import pipeline, step
from zenml.client import Client

ARTIFACT_NAME = "predictions"
PIPELINE_NAME = "bar"


@step
def producer(return_value: int) -> Annotated[int, ARTIFACT_NAME]:
    """Step producing versioned output."""
    return return_value


@step
def consumer(external_artifact: int, expected_value: int):
    """Step receiving external artifact and asserting it."""
    assert external_artifact == expected_value


@pipeline(name=PIPELINE_NAME, enable_cache=False)
def producer_pipeline(return_value: int):
    producer(return_value)


@pipeline(name="something_else", enable_cache=False)
def producer_pipeline_2(return_value: int):
    producer(return_value)


@pipeline(enable_cache=False)
def consumer_pipeline(
    expected_value: int,
    value: Optional[Any] = None,
    id: Optional[UUID] = None,
):
    artifact = None
    if value:
        artifact = value
    elif id:
        artifact = Client().get_artifact_version(id)

    consumer(
        artifact,
        expected_value=expected_value,
    )


def test_external_artifact_by_value(clean_client: Client):
    """Test passing external artifact by value."""
    consumer_pipeline(value=42, expected_value=42)


def test_external_artifact_by_id(clean_client: Client):
    """Test passing external artifact by ID."""
    producer_pipeline(return_value=42)
    artifact_version_id = (
        producer_pipeline.model.last_successful_run.artifact_versions[0].id
    )
    consumer_pipeline(id=artifact_version_id, expected_value=42)
