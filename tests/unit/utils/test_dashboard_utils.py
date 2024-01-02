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

from unittest.mock import MagicMock

from hypothesis import given, settings
from hypothesis.strategies import text

from zenml.client import Client
from zenml.utils import dashboard_utils


@given(text())
@settings(deadline=None)
def test_get_run_url_works_without_server(random_text):
    """Test that the get_run_url function works without a server."""
    if Client().zen_store.type == "sql":
        url = dashboard_utils.get_run_url(random_text)
        assert url is None


def test_get_run_url_works_with_mocked_server(monkeypatch):
    """Test that the get_run_url function works with a server."""
    mock_url = MagicMock()
    mock_runs = MagicMock()
    mock_store_type = MagicMock()

    mock_url.return_value = "https://aria_rules.com"
    mock_runs.return_value = []
    mock_store_type.return_value = "rest"

    monkeypatch.setattr(
        "zenml.zen_stores.sql_zen_store.SqlZenStore.url", mock_url
    )
    monkeypatch.setattr(
        "zenml.zen_stores.sql_zen_store.SqlZenStore.list_runs", mock_runs
    )
    monkeypatch.setattr(
        "zenml.zen_stores.sql_zen_store.SqlZenStore.type", mock_store_type
    )

    if Client().zen_store.type == "rest":
        url = dashboard_utils.get_run_url("test")
        assert url == "https://aria_rules.com/pipelines/all-runs"
        assert isinstance(url, str)


def test_get_run_url_works_with_mocked_server_with_runs(monkeypatch):
    """Test that the get_run_url function works with a server and runs."""
    mock_url = MagicMock()
    mock_runs = MagicMock()
    mock_store_type = MagicMock()

    mock_url.return_value = "https://aria_rules.com"
    mock_runs.return_value = [{"id": "axel"}]
    mock_store_type.return_value = "rest"

    monkeypatch.setattr(
        "zenml.zen_stores.sql_zen_store.SqlZenStore.url", mock_url
    )
    monkeypatch.setattr(
        "zenml.zen_stores.sql_zen_store.SqlZenStore.list_runs", mock_runs
    )
    monkeypatch.setattr(
        "zenml.zen_stores.sql_zen_store.SqlZenStore.type", mock_store_type
    )

    if Client().zen_store.type == "rest":
        url = dashboard_utils.get_run_url(
            run_name="aria", pipeline_id="blupus"
        )
        assert url == "https://aria_rules.com/pipelines/blupus/runs/axel/dag"
        assert isinstance(url, str)
