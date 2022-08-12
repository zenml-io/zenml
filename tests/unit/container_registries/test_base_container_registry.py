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
from contextlib import ExitStack as does_not_raise
from typing import ClassVar

import pytest

from zenml.container_registries import BaseContainerRegistry


class StubContainerRegistry(BaseContainerRegistry):
    """Class to test the abstract BaseContainerRegistry."""

    FLAVOR: ClassVar[str] = "test"


def test_base_container_registry_removes_trailing_slashes():
    """Tests that the base container registry removes trailing slashes from
    the URI.
    """
    assert StubContainerRegistry(name="", uri="test/").uri == "test"


def test_base_container_registry_requires_authentication_if_secret_provided():
    """Tests that the base container registry requires authentication if a
    secret name is provided.
    """
    assert (
        StubContainerRegistry(name="", uri="").requires_authentication is False
    )
    assert (
        StubContainerRegistry(
            name="", uri="", authentication_secret="secret"
        ).requires_authentication
        is True
    )


def test_base_container_registry_local_property():
    """Tests the base container registry `is_local` property."""
    assert StubContainerRegistry(name="", uri="localhost:8000").is_local is True
    assert StubContainerRegistry(name="", uri="gcr.io").is_local is False


def test_base_container_registry_prevents_push_if_uri_does_not_match(mocker):
    """Tests the base container registry push only works if the URI matches."""
    mocker.patch("zenml.utils.docker_utils.push_image")

    registry = StubContainerRegistry(name="", uri="some_uri")
    with does_not_raise():
        registry.push_image("some_uri/image_name")

    with pytest.raises(ValueError):
        registry.push_image("wrong_uri/image_name")
