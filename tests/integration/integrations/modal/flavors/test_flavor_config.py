#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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

import pytest
from pydantic import ValidationError

from zenml.integrations.modal import MODAL_STEP_OPERATOR_FLAVOR
from zenml.integrations.modal.flavors.modal_step_operator_flavor import (
    DEFAULT_TIMEOUT_SECONDS,
    ModalStepOperatorConfig,
    ModalStepOperatorFlavor,
    ModalStepOperatorSettings,
)


def test_modal_settings_default_timeout() -> None:
    settings = ModalStepOperatorSettings()
    assert settings.timeout == DEFAULT_TIMEOUT_SECONDS


def test_modal_config_is_remote_true() -> None:
    cfg = ModalStepOperatorConfig()
    assert cfg.is_remote is True


def test_modal_flavor_name_constant() -> None:
    flavor = ModalStepOperatorFlavor()
    assert flavor.name == MODAL_STEP_OPERATOR_FLAVOR


def test_modal_settings_timeout_accepts_valid_values() -> None:
    # Test minimum valid value
    settings = ModalStepOperatorSettings(timeout=1)
    assert settings.timeout == 1

    # Test maximum valid value
    settings = ModalStepOperatorSettings(timeout=DEFAULT_TIMEOUT_SECONDS)
    assert settings.timeout == DEFAULT_TIMEOUT_SECONDS

    # Test mid-range value
    settings = ModalStepOperatorSettings(timeout=3600)
    assert settings.timeout == 3600


def test_modal_settings_timeout_rejects_below_minimum() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ModalStepOperatorSettings(timeout=0)

    assert "greater than or equal to 1" in str(exc_info.value)


def test_modal_settings_timeout_rejects_above_maximum() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ModalStepOperatorSettings(timeout=DEFAULT_TIMEOUT_SECONDS + 1)

    assert "less than or equal to" in str(exc_info.value)


def test_modal_settings_timeout_rejects_negative() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ModalStepOperatorSettings(timeout=-1)

    assert "greater than or equal to 1" in str(exc_info.value)
