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
import pytest

from zenml.integrations.deepchecks.validation_checks import (
    DeepchecksValidationCheck,
)


def test_validation_check_fails_when_checking_name():
    """Ensures that the validation check fails when names not using our format."""
    deepchecks_validation_check = DeepchecksValidationCheck(
        "aria", "the_wrong_enum_value"
    )
    with pytest.raises(ValueError):
        deepchecks_validation_check.validate_check_name("abc")
