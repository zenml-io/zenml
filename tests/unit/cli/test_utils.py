#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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
from zenml.cli import cli
from zenml.cli.utils import parse_name_and_extra_arguments
from zenml.client import Client
from zenml.enums import PermissionType
from zenml.models import (
    RoleResponseModel,
    TeamResponseModel,
    UserResponseModel,
    WorkspaceResponseModel,
)

SAMPLE_CUSTOM_ARGUMENTS = [
    '--custom_argument="value"',
    '--food="chicken biryani"',
    "axl",
    '--best_cat="aria"',
]
SAMPLE_ROLE = "cat_feeder"
SAMPLE_PROJECT = "cat_prj"


# ----- #
# USERS #
# ----- #
SAMPLE_USER = "aria"
user_create_command = cli.commands["user"].commands["create"]
user_update_command = cli.commands["user"].commands["update"]
user_delete_command = cli.commands["user"].commands["delete"]


def create_sample_user(clean_client: Client) -> UserResponseModel:
    """Fixture to get a clean global configuration and repository for an
    individual test.

    Args:
        clean_client: Clean client
    """
    return clean_client.create_user(name=SAMPLE_USER, password="catnip")


# ----- #
# TEAMS #
# ----- #
SAMPLE_TEAM = "felines"
team_create_command = cli.commands["team"].commands["create"]
team_update_command = cli.commands["team"].commands["update"]
team_list_command = cli.commands["team"].commands["list"]
team_describe_command = cli.commands["team"].commands["describe"]
team_delete_command = cli.commands["team"].commands["delete"]


def create_sample_team(clean_client: Client) -> TeamResponseModel:
    """Fixture to get a clean global configuration and repository for an
    individual test.

    Args:
        clean_client: Clean client
    """
    return clean_client.create_team(name=SAMPLE_TEAM)


def test_parse_name_and_extra_arguments_returns_a_dict_of_known_options() -> None:
    """Check that parse_name_and_extra_arguments returns a dict of known options"""
    name, parsed_sample_args = parse_name_and_extra_arguments(
        SAMPLE_CUSTOM_ARGUMENTS
    )
    assert isinstance(parsed_sample_args, dict)
    assert len(parsed_sample_args.values()) == 3
    assert parsed_sample_args["best_cat"] == '"aria"'
    assert isinstance(name, str)
    assert name == "axl"


def create_sample_role(clean_client: Client) -> RoleResponseModel:
    """Fixture to get a global configuration with a  role.

    Args:
        clean_client: Clean client
    """
    return clean_client.create_role(
        name=SAMPLE_ROLE, permissions_list=[PermissionType.READ]
    )


def create_sample_project(clean_client: Client) -> WorkspaceResponseModel:
    """Fixture to get a global configuration with a  role.

    Args:
        clean_client: Clean client
    """
    return clean_client.create_project(
        name=SAMPLE_PROJECT,
        description="This project aims to ensure world domination for all "
        "cat-kind.",
    )
