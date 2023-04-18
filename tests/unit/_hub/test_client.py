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
"""Unit tests for the ZenML Hub client."""

from src.zenml.constants import ENV_ZENML_HUB_URL

from zenml._hub.client import HubClient
from zenml._hub.constants import ZENML_HUB_DEFAULT_URL


def test_default_url(mocker):
    """Test that the default URL is set correctly."""
    client = HubClient()
    assert client.url == ZENML_HUB_DEFAULT_URL

    # Pass a URL to the constructor.
    client = HubClient(url="test_url")
    assert client.url == "test_url"

    # Mock setting the environment variable.
    mocker.patch.dict("os.environ", {ENV_ZENML_HUB_URL: "test_url"})
    client = HubClient()
    assert client.url == "test_url"


def test_list_plugins():
    """Test listing plugins."""
    client = HubClient()
    plugins = client.list_plugins()
    assert len(plugins) > 0


def test_get_plugin():
    """Test getting a plugin."""
    plugin_name = "langchain_qa_example"
    client = HubClient()
    plugin = client.get_plugin(plugin_name)
    assert plugin.name == plugin_name

    # Test getting a specific version.
    version = "0.1"
    plugin = client.get_plugin(plugin_name, version=version)
    assert plugin.name == plugin_name
    assert plugin.version == version

    # Test getting a non-existent plugin.
    plugin_name = "non_existent_plugin_by_aria_and_blupus"
    client = HubClient()
    plugin = client.get_plugin(plugin_name)
    assert plugin is None
