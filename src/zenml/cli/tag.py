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
"""CLI functionality to interact with tags."""
# from functools import partial
from typing import Any, Optional, Union
from uuid import UUID

import click

# from uuid import UUID
# import click
from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.client import Client
from zenml.enums import CliCategories, ColorVariants
from zenml.exceptions import EntityExistsError
from zenml.logger import get_logger
from zenml.models.tag_models import (
    TagFilterModel,
    TagRequestModel,
    TagUpdateModel,
)
from zenml.utils.dict_utils import remove_none_values

logger = get_logger(__name__)


@cli.group(cls=TagGroup, tag=CliCategories.MANAGEMENT_TOOLS)
def tag() -> None:
    """Interact with tags."""


@cli_utils.list_options(TagFilterModel)
@tag.command("list", help="List tags with filter.")
def list_tags(**kwargs: Any) -> None:
    """List tags with filter.

    Args:
        **kwargs: Keyword arguments to filter models.
    """
    tags = Client().list_tags(TagFilterModel(**kwargs))

    if not tags:
        cli_utils.declare("No tags found.")
        return

    cli_utils.print_pydantic_models(
        tags,
        exclude_columns=["created"],
    )


@tag.command("register", help="Register a new tag.")
@click.option(
    "--name",
    "-n",
    help="The name of the tag.",
    type=str,
    required=True,
)
@click.option(
    "--color",
    "-c",
    help="The color variant for UI.",
    type=click.Choice(choices=ColorVariants.values()),
    required=False,
)
def register_tag(name: str, color: Optional[ColorVariants]) -> None:
    """Register a new model in the Model Control Plane.

    Args:
        name: The name of the tag.
        color: The color variant for UI.
    """
    request_dict = remove_none_values(dict(name=name, color=color))
    try:
        tag = Client().create_tag(TagRequestModel(**request_dict))
    except (EntityExistsError, ValueError) as e:
        cli_utils.error(str(e))

    cli_utils.print_pydantic_models(
        [tag],
        exclude_columns=["created"],
    )


@tag.command("update", help="Update an existing tag.")
@click.argument("tag_name_or_id")
@click.option(
    "--name",
    "-n",
    help="The name of the tag.",
    type=str,
    required=False,
)
@click.option(
    "--color",
    "-c",
    help="The color variant for UI.",
    type=click.Choice(choices=ColorVariants.values()),
    required=False,
)
def update_tag(
    tag_name_or_id: Union[str, UUID], name: Optional[str], color: Optional[str]
) -> None:
    """Register a new model in the Model Control Plane.

    Args:
        tag_name_or_id: The name or ID of the tag.
        name: The name of the tag.
        color: The color variant for UI.
    """
    update_dict = remove_none_values(dict(name=name, color=color))
    if not update_dict:
        cli_utils.declare("You need to specify --name or --color for update.")
        return

    tag = Client().update_tag(
        tag_name_or_id=tag_name_or_id,
        tag_update_model=TagUpdateModel(**update_dict),
    )

    cli_utils.print_pydantic_models(
        [tag],
        exclude_columns=["created"],
    )


@tag.command("delete", help="Delete an existing tag.")
@click.argument("tag_name_or_id")
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Don't ask for confirmation.",
)
def delete_tag(
    tag_name_or_id: Union[str, UUID],
    yes: bool = False,
) -> None:
    """Delete an existing tag.

    Args:
        tag_name_or_id: The ID or name of the tag to delete.
        yes: If set, don't ask for confirmation.
    """
    try:
        tagged_count = Client().get_tag(tag_name_or_id).tagged_count
    except (KeyError, ValueError) as e:
        cli_utils.error(str(e))

    if not yes or tagged_count > 0:
        confirmation = cli_utils.confirmation(
            f"Are you sure you want to delete tag '{tag_name_or_id}'?"
            + (
                ""
                if tagged_count == 0
                else f"\n{tagged_count} objects are tagged with it."
            )
        )
        if not confirmation:
            cli_utils.declare("Tag deletion canceled.")
            return

    try:
        Client().delete_tag(
            tag_name_or_id=tag_name_or_id,
        )
    except (KeyError, ValueError) as e:
        cli_utils.error(str(e))
    else:
        cli_utils.declare(f"Tag '{tag_name_or_id}' deleted.")
