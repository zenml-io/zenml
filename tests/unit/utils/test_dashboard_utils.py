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

from hypothesis import given
from hypothesis.strategies import text

from zenml.client import Client
from zenml.utils import dashboard_utils


@given(text())
def test_get_run_url_works_without_server(random_text):
    """Test that the get_run_url function works without a server."""
    if Client().zen_store.type == "sql":
        url = dashboard_utils.get_run_url(random_text)
        assert url == ""
        assert isinstance(url, str)
