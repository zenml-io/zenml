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

from zenml.enums import StackComponentType
from zenml.integrations.feast.feature_stores import FeastFeatureStore


@pytest.fixture()
def feast_feature_store():
    """Fixture to yield a Feast feature store."""
    feast_feature_store = FeastFeatureStore(name="", feast_repo="")
    yield feast_feature_store


def test_feast_feature_store_attributes(feast_feature_store):
    """Tests that the basic attributes of the feast feature store are set
    correctly."""
    assert feast_feature_store.TYPE == StackComponentType.FEATURE_STORE
    assert feast_feature_store.FLAVOR == "feast"
    assert feast_feature_store.online_host == "localhost"
    assert feast_feature_store.online_port == 6379
