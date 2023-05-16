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
from contextlib import ExitStack as does_not_raise

import pytest

from zenml.config import DockerSettings
from zenml.config.base_settings import BaseSettings
from zenml.config.settings_resolver import SettingsResolver
from zenml.exceptions import SettingsResolvingError


def test_settings_resolver_fails_when_using_invalid_settings_key(mocker):
    """Tests that the settings resolver can't be initialized with an invalid
    settings key."""
    mocker.patch(
        "zenml.utils.settings_utils.is_valid_setting_key", return_value=True
    )
    with does_not_raise():
        SettingsResolver(key="", settings=BaseSettings())

    mocker.patch(
        "zenml.utils.settings_utils.is_valid_setting_key", return_value=False
    )

    with pytest.raises(ValueError):
        SettingsResolver(key="", settings=BaseSettings())


def test_resolving_general_settings(local_stack):
    """Tests resolving general settings."""
    settings = BaseSettings(parent_image="parent_image")

    resolver = SettingsResolver(key="docker", settings=settings)
    resolved_settings = resolver.resolve(stack=local_stack)
    assert isinstance(resolved_settings, DockerSettings)
    assert resolved_settings.parent_image == "parent_image"


def test_resolving_stack_component_settings(mocker, local_stack):
    """Tests resolving of stack component settings."""

    class TestSettings(BaseSettings):
        pass

    mocker.patch.object(
        type(local_stack),
        "setting_classes",
        new_callable=mocker.PropertyMock,
        return_value={"orchestrator.TEST_FLAVOR": TestSettings},
    )

    resolver = SettingsResolver(
        key="orchestrator.TEST_FLAVOR", settings=BaseSettings()
    )
    resolved_settings = resolver.resolve(stack=local_stack)
    assert isinstance(resolved_settings, TestSettings)


def test_resolving_fails_if_no_stack_component_settings_exist_for_the_given_key(
    local_stack,
):
    """Tests that resolving fails if the key refers to settings which don't
    exist in the given stack."""
    resolver = SettingsResolver(
        key="orchestrator.not_a_flavor_in_the_stack", settings=BaseSettings()
    )
    with pytest.raises(KeyError):
        resolver.resolve(stack=local_stack)


def test_resolving_fails_if_the_settings_cant_be_converted(local_stack):
    """Tests that resolving fails if the given settings can't be converted to
    the expected settings class."""
    settings = BaseSettings(not_a_docker_settings_key=1)

    resolver = SettingsResolver(key="docker", settings=settings)

    with pytest.raises(SettingsResolvingError):
        resolver.resolve(stack=local_stack)
