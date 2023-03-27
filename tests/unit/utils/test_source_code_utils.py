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
import pytest

from zenml.utils import source_code_utils


def test_get_source():
    """Tests if source of objects is gotten properly."""
    assert source_code_utils.get_source_code(pytest.Cache)


def test_get_hashed_source():
    """Tests if hash of objects is computed properly."""
    assert source_code_utils.get_hashed_source_code(pytest.Cache)
