#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Utils for schemas."""

import json
import math
from typing import Dict, List, Type, TypeVar

from sqlmodel import Relationship

from zenml.metadata.metadata_types import MetadataType
from zenml.models import BaseResponse, Page, RunMetadataEntry
from zenml.zen_stores.schemas.base_schemas import BaseSchema

S = TypeVar("S", bound=BaseSchema)


def get_page_from_list(
    items_list: List[S],
    response_model: Type[BaseResponse],  # type: ignore[type-arg]
    size: int = 5,
    page: int = 1,
    include_resources: bool = False,
    include_metadata: bool = False,
) -> Page[BaseResponse]:  # type: ignore[type-arg]
    """Converts list of schemas into page of response models.

    Args:
        items_list: List of schemas
        response_model: Response model
        size: Page size
        page: Page number
        include_metadata: Whether metadata should be included in response models
        include_resources: Whether resources should be included in response models

    Returns:
        A page of list items.
    """
    total = len(items_list)
    if total == 0:
        total_pages = 1
    else:
        total_pages = math.ceil(total / size)

    start = (page - 1) * size
    end = start + size

    page_items = [
        item.to_model(
            include_metadata=include_metadata,
            include_resources=include_resources,
        )
        for item in items_list[start:end]
    ]
    return Page[response_model](  # type: ignore[valid-type]
        index=page,
        max_size=size,
        total_pages=total_pages,
        total=total,
        items=page_items,
    )


class RunMetadataInterface:
    """The interface for entities with run metadata."""

    run_metadata = Relationship()

    def fetch_metadata_collection(self) -> Dict[str, List[RunMetadataEntry]]:
        """Fetches all the metadata entries related to the entity.

        Returns:
            A dictionary, where the key is the key of the metadata entry
                and the values represent the list of entries with this key.
        """
        metadata_collection: Dict[str, List[RunMetadataEntry]] = {}

        for rm in self.run_metadata:
            if rm.key not in metadata_collection:
                metadata_collection[rm.key] = []
            metadata_collection[rm.key].append(
                RunMetadataEntry(
                    value=json.loads(rm.value),
                    created=rm.created,
                )
            )

        return metadata_collection

    def fetch_metadata(self) -> Dict[str, MetadataType]:
        """Fetches the latest metadata entry related to the entity.

        Returns:
            A dictionary, where the key is the key of the metadata entry
                and the values represent the latest entry with this key.
        """
        metadata_collection = self.fetch_metadata_collection()
        return {
            k: sorted(v, key=lambda x: x.created, reverse=True)[0].value
            for k, v in metadata_collection.items()
        }


def get_resource_type_name(schema_class: Type[BaseSchema]) -> str:
    """Get the name of a resource from a schema class.

    Args:
        schema_class: The schema class to get the name of.

    Returns:
        The name of the resource.
    """
    entity_name = schema_class.__tablename__
    assert isinstance(entity_name, str)
    # Some entities are plural, some are singular, some have multiple words
    # in their table name connected by underscores (e.g. pipeline_run)
    return entity_name.replace("_", " ").rstrip("s")
