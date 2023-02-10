#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import sys

import pytest
from hypothesis import given
from hypothesis.strategies import text

from zenml.exceptions import ValidationError

if sys.version_info.major == 3 and sys.version_info.minor != 10:
    from zenml.integrations.kserve.services.kserve_deployment import (
        KServeDeploymentConfig,
    )
    from zenml.integrations.kserve.steps.kserve_deployer import (
        KServeDeployerStepParameters,
    )
    from zenml.integrations.kserve.steps.kserve_step_utils import (
        is_valid_model_name,
        prepare_service_config,
    )


@pytest.mark.skipif(
    sys.version_info.major == 3 and sys.version_info.minor == 10,
    reason="Kserve is only supported on Python <3.10",
)
@given(
    sample_str=text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1
    )
)
def test_model_name_validation(sample_str: str):
    """Tests that model name validation is working."""
    assert is_valid_model_name(sample_str)

    invalid_characters = "!@#$%^&*()_+|}{:?><,./;'[]\\=`~"
    for invalid_char in invalid_characters:
        invalid_str_start = invalid_char + sample_str
        invalid_str_end = sample_str + invalid_char
        assert not is_valid_model_name(invalid_str_start)
        assert not is_valid_model_name(invalid_str_end)
        assert not is_valid_model_name(invalid_char)


@pytest.mark.skipif(
    sys.version_info.major == 3 and sys.version_info.minor == 10,
    reason="Kserve is only supported on Python <3.10",
)
def test_service_config_preparation_fails_with_invalid_model_name():
    """Test that the prepare_service_config function fails with invalid input."""
    with pytest.raises(ValidationError):
        prepare_service_config(
            model_uri="",
            output_artifact_uri="",
            params=KServeDeployerStepParameters(
                service_config=KServeDeploymentConfig(
                    model_name="aria_loves_blupus", predictor="pytorch"
                )
            ),
        )
