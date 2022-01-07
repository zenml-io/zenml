#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

import inspect

import pytest

from zenml.utils import source_utils


def test_is_third_party_module():
    """Tests that third party modules get detected correctly."""
    third_party_file = inspect.getfile(pytest.Cache)
    assert source_utils.is_third_party_module(third_party_file)

    non_third_party_file = inspect.getfile(source_utils)
    assert not source_utils.is_third_party_module(non_third_party_file)
