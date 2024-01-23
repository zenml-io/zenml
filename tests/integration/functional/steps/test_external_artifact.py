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


from typing import Any

import pytest
from typing_extensions import Annotated

from zenml import pipeline, step
from zenml.artifacts.external_artifact import ExternalArtifact
from zenml.client import Client

ARTIFACT_NAME = "predictions"
PIPELINE_NAME = "bar"


@step
def producer(return_value: int) -> Annotated[int, ARTIFACT_NAME]:
    """Step producing versioned output."""
    return return_value


@step
def consumer(external_artifact: Any, expected_value: int):
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
    value: Any,
):
    consumer(
        ExternalArtifact(
            value=value,
        ),
        expected_value=value,
    )


def test_external_artifact_with_valid_value(clean_client: Client):
    """Test passing external artifact by value."""
    consumer_pipeline(value=42)


def test_external_artifact_raises_on_empty_value(clean_client: Client):
    """Test passing external artifact by value."""
    with pytest.raises(RuntimeError):
        consumer_pipeline(value="")
    with pytest.raises(RuntimeError):
        consumer_pipeline(value=None)
