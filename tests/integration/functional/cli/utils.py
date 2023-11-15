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
from contextlib import contextmanager
from typing import Generator, Optional, Tuple

from tests.harness.harness import TestHarness
from zenml.cli import cli
from zenml.cli.utils import (
    parse_name_and_extra_arguments,
    temporary_active_stack,
)
from zenml.client import Client
from zenml.enums import PermissionType
from zenml.models import (
    RoleResponseModel,
    TeamResponseModel,
    UserResponseModel,
    WorkspaceResponseModel,
)
from zenml.models.tag_models import TagFilterModel, TagRequestModel
from zenml.utils.string_utils import random_str

SAMPLE_CUSTOM_ARGUMENTS = [
    '--custom_argument="value"',
    '--food="chicken biryani"',
    "axl",
    '--best_cat="aria"',
]


# ----- #
# USERS #
# ----- #
user_create_command = cli.commands["user"].commands["create"]
user_update_command = cli.commands["user"].commands["update"]
user_delete_command = cli.commands["user"].commands["delete"]


def sample_name(prefix: str = "aria") -> str:
    """Function to get random username."""
    return f"{prefix}-{random_str(4)}".lower()


def create_sample_user(
    prefix: Optional[str] = None,
    password: Optional[str] = None,
    initial_role: Optional[str] = None,
) -> UserResponseModel:
    """Function to create a sample user."""
    return Client().create_user(
        name=sample_name(prefix),
        password=password if password is not None else random_str(16),
        initial_role=initial_role,
    )


@contextmanager
def create_sample_user_and_login(
    prefix: Optional[str] = None,
    initial_role: Optional[str] = None,
) -> Generator[Tuple[UserResponseModel, Client], None, None]:
    """Context manager to create a sample user and login with it."""
    password = random_str(16)
    user = create_sample_user(prefix, password, initial_role)

    deployment = TestHarness().active_deployment
    with deployment.connect(
        custom_username=user.name,
        custom_password=password,
    ) as client:
        yield user, client


# ----- #
# TEAMS #
# ----- #
team_create_command = cli.commands["team"].commands["create"]
team_update_command = cli.commands["team"].commands["update"]
team_list_command = cli.commands["team"].commands["list"]
team_describe_command = cli.commands["team"].commands["describe"]
team_delete_command = cli.commands["team"].commands["delete"]


def sample_team_name() -> str:
    """Function to get random team name."""
    return f"felines_{random_str(4)}"


def create_sample_team() -> TeamResponseModel:
    """Fixture to get a clean global configuration and repository for an individual test."""
    return Client().create_team(name=sample_team_name())


def test_parse_name_and_extra_arguments_returns_a_dict_of_known_options() -> (
    None
):
    """Check that parse_name_and_extra_arguments returns a dict of known options."""
    name, parsed_sample_args = parse_name_and_extra_arguments(
        SAMPLE_CUSTOM_ARGUMENTS
    )
    assert isinstance(parsed_sample_args, dict)
    assert len(parsed_sample_args.values()) == 3
    assert parsed_sample_args["best_cat"] == '"aria"'
    assert isinstance(name, str)
    assert name == "axl"


def sample_role_name() -> str:
    """Function to get random role name."""
    return f"cat_feeder_{random_str(4)}"


def create_sample_role() -> RoleResponseModel:
    """Fixture to get a global configuration with a  role."""
    return Client().create_role(
        name=sample_role_name(), permissions_list=[PermissionType.READ]
    )


def sample_workspace_name() -> str:
    """Function to get random workspace name."""
    return f"cat_prj_{random_str(4)}"


def create_sample_workspace() -> WorkspaceResponseModel:
    """Fixture to get a global configuration with a  role."""
    return Client().create_workspace(
        name=sample_workspace_name(),
        description="This workspace aims to ensure world domination for all "
        "cat-kind.",
    )


# ------- #
# SECRETS #
# ------- #


@contextmanager
def cleanup_secrets(
    name_prefix: Optional[str] = None,
) -> Generator[str, None, None]:
    """Context manager to generate a sample prefix for secret names and to clean
    up whatever secrets are created with that prefix on exit.

    Args:
        name_prefix: An optional prefix to use to generate the name prefix (yes,
            you read that right, the prefix to the prefix).

    Yields:
        A name prefix to be used for secret names.
    """
    name_prefix = sample_name(name_prefix or "axl-secret-service")
    yield name_prefix

    # Clean up
    client = Client()
    secrets = client.list_secrets(name=f"startswith:{name_prefix}")
    for secret in secrets.items:
        try:
            client.delete_secret(secret.id)
        except KeyError:
            pass


def test_temporarily_setting_the_active_stack(clean_workspace):
    """Tests the context manager to temporarily activate a stack."""
    initial_stack = clean_workspace.active_stack_model
    components = {
        key: components[0].id
        for key, components in initial_stack.components.items()
    }
    new_stack = clean_workspace.create_stack(name="new", components=components)

    with temporary_active_stack():
        assert clean_workspace.active_stack_model == initial_stack

    with temporary_active_stack(stack_name_or_id=new_stack.id):
        assert clean_workspace.active_stack_model == new_stack

    assert clean_workspace.active_stack_model == initial_stack


@contextmanager
def tags_killer(tag_create_count: int = 5):
    tags = []
    for _ in range(tag_create_count):
        tags.append(
            Client().create_tag(TagRequestModel(name=random_resource_name()))
        )
    yield tags
    for tag in Client().list_tags(TagFilterModel(size=999)).items:
        Client().delete_tag(tag.id)


def random_resource_name(length: int = 32) -> str:
    import random
    import string

    return "".join(
        random.choice(string.ascii_lowercase + string.digits)
        for _ in range(length)
    )
