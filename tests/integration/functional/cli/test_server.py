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

from click.testing import CliRunner

from tests.integration.functional.cli.test_utils import (
    sample_role_name,
    sample_user_name,
    user_create_command,
)
from zenml.cli.cli import cli
from zenml.config.global_config import GlobalConfiguration

role_create_command = cli.commands["role"].commands["create"]


def test_server_doesnt_raise_error_for_permissionless_user() -> None:
    """Test that the server doesn't raise an error for a permissionless user."""
    runner = CliRunner()

    new_role_name = sample_role_name()
    new_user_name = sample_user_name()
    new_password = "kamicat"

    # create a role without any permissions
    runner.invoke(role_create_command, [new_role_name])

    # create a user with the permissionless role
    runner.invoke(
        user_create_command,
        [
            new_user_name,
            f"--password={new_password}",
            f"--role={new_role_name}",
        ],
    )

    # disconnect from the server
    runner.invoke(cli.commands["disconnect"])

    server_url = GlobalConfiguration().store.url
    # try to connect to the server with the permissionless user
    with does_not_raise():
        result = runner.invoke(
            cli.commands["connect"],
            [
                f"--url={server_url}",
                f"--user={new_user_name}",
                f"--password={new_password}",
            ],
        )
        assert result.exit_code == 0
