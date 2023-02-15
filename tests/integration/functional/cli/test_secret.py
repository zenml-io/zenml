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
"""Tests for the Secret Store CLI."""
from click.testing import CliRunner

from zenml.cli.cli import cli
from zenml.client import Client


def test_create_secret(clean_client):
    """Test that creating a new secret succeeds."""
    secret_create_command = cli.commands["secret"].commands["create"]
    runner = CliRunner()
    result = runner.invoke(
        secret_create_command,
        ["test_secret", "--test_value=aria", "--test_value2=blupus"],
    )
    assert result.exit_code == 0
    client = Client()
    created_secret = client.get_secret("test_secret")
    assert created_secret is not None
    assert created_secret.values["test_value"].get_secret_value() == "aria"
    assert created_secret.values["test_value2"].get_secret_value() == "blupus"
