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
"""Utility functions for handling tags."""

from typing import List
from uuid import UUID

from zenml.enums import TaggableResourceTypes
from zenml.exceptions import EntityExistsError
from zenml.models.tag_models import TagRequestModel, TagResourceRequestModel
from zenml.utils.uuid_utils import generate_uuid_from_string


def _get_tag_resource_id(tag_id: UUID, resource_id: UUID) -> UUID:
    return generate_uuid_from_string(str(tag_id) + str(resource_id))


def create_links(
    tag_names: List[str],
    resource_id: UUID,
    resource_type: TaggableResourceTypes,
) -> None:
    """Creates a tag<>resource link if not present.

    Args:
        tag_names: The list of names of the tags.
        resource_id: The id of the resource.
        resource_type: The type of the resource to create link with
    """
    from zenml.client import Client

    client = Client()
    for tag_name in tag_names:
        try:
            tag = client.get_tag(tag_name)
        except KeyError:
            tag = client.create_tag(TagRequestModel(name=tag_name))
        try:
            client.zen_store.create_tag_resource(
                TagResourceRequestModel(
                    tag_id=tag.id,
                    resource_id=resource_id,
                    resource_type=resource_type,
                )
            )
        except EntityExistsError:
            pass


def remove_links(
    tag_names: List[str],
    resource_id: UUID,
) -> None:
    """Deletes tag<>resource link if present.

    Args:
        tag_names: The list of names of the tags.
        resource_id: The id of the resource.
    """
    from zenml.client import Client

    client = Client()
    for tag_name in tag_names:
        try:
            tag = client.get_tag(tag_name)
            client.zen_store.delete_tag_resource(
                _get_tag_resource_id(tag.id, resource_id)
            )
        except KeyError:
            pass
