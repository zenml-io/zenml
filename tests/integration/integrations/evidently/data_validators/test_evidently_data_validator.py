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

from datetime import datetime
from uuid import uuid4

from zenml.enums import StackComponentType
from zenml.integrations.evidently import EVIDENTLY_DATA_VALIDATOR_FLAVOR
from zenml.integrations.evidently.data_validators import EvidentlyDataValidator


def test_evidently_data_validator_attributes():
    """Tests that the basic attributes of the Evidently data validator are set correctly."""
    validator = EvidentlyDataValidator(
        name="arias_validator",
        id=uuid4(),
        config={},
        flavor="evidently",
        type=StackComponentType.DATA_VALIDATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )
    assert validator.type == StackComponentType.DATA_VALIDATOR
    assert validator.flavor == EVIDENTLY_DATA_VALIDATOR_FLAVOR
    assert validator.name == "arias_validator"
    assert validator.NAME == "Evidently"
