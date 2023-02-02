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

from zenml.integrations.deepchecks.validation_checks.tabular_validation_checks import (
    DeepchecksTabularDataValidationCheck,
)


def test_validate_check_name_succeeds_for_supported_check_name():
    """Ensure that the name validation succeeds for supported names."""
    check = DeepchecksTabularDataValidationCheck.TABULAR_IS_SINGLE_VALUE
    with does_not_raise():
        check.validate_check_name("deepchecks.tabular.checks.something")


@pytest.mark.parametrize(
    "wrong_check_name",
    [
        "aria",  # not a path at all
        "the.wrong.check",  # not a deepchecks path
        "deepchecks.vision.checks.something",  # should be tabular not vision
    ],
)
def test_validate_check_name_fails_for_unsupported_names(wrong_check_name):
    """Ensure that the name validation fails for unsupported names."""
    check = DeepchecksTabularDataValidationCheck.TABULAR_IS_SINGLE_VALUE
    with pytest.raises(ValueError):
        check.validate_check_name(wrong_check_name)
