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

import sys
from datetime import datetime
from uuid import uuid4

import pytest

from zenml.enums import StackComponentType


@pytest.mark.skipif(
    sys.version_info.minor == 12,
    reason="The deepchecks integrations is not yet supported on 3.12.",
)
def test_deepchecks_data_validator_attributes():
    """Tests that the basic attributes of the Deepchecks data validator are set correctly."""
    from zenml.integrations.deepchecks import DEEPCHECKS_DATA_VALIDATOR_FLAVOR
    from zenml.integrations.deepchecks.data_validators import (
        DeepchecksDataValidator,
    )

    validator = DeepchecksDataValidator(
        name="arias_validator",
        id=uuid4(),
        config={},
        flavor="deepchecks",
        type=StackComponentType.DATA_VALIDATOR,
        user=uuid4(),
        workspace=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )
    assert validator.type == StackComponentType.DATA_VALIDATOR
    assert validator.flavor == DEEPCHECKS_DATA_VALIDATOR_FLAVOR
    assert validator.name == "arias_validator"
    assert validator.NAME == "Deepchecks"
