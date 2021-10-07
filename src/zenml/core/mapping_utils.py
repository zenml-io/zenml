import os
from pathlib import Path
from typing import Dict
from uuid import UUID

from pydantic import BaseModel

from zenml.core.base_component import BaseComponent
from zenml.utils import path_utils, source_utils


class UUIDSourceTuple(BaseModel):
    """Container used to store UUID and source information
    of a single BaseComponent subclass.

    Attributes:
        uuid: Identifier of the BaseComponent
        source: Contains the fully qualified class name and information
         about a git hash/tag. E.g. foo.bar.BaseComponentSubclass@git_tag
    """

    uuid: UUID
    source: str


def get_key_from_uuid(uuid: UUID, mapping: Dict[str, UUIDSourceTuple]) -> str:
    """Return they key that points to a certain uuid in a mapping.

    Args:
        uuid: uuid to query.
        mapping: Dict mapping keys to UUIDs and source information.

    Returns:
        Returns the key from the mapping.
    """
    inverted_map = {v.uuid: k for k, v in mapping.items()}
    return inverted_map[uuid]


def get_component_from_key(
    key: str, mapping: Dict[str, UUIDSourceTuple]
) -> BaseComponent:
    """Given a key and a mapping, return an initialized component.

    Args:
        key: Unique key.
        mapping: Dict of type str -> UUIDSourceTuple.

    Returns:
        An object which is a subclass of type BaseComponent.
    """
    tuple_ = mapping[key]
    class_ = source_utils.load_source_path_class(tuple_.source)
    return class_(uuid=tuple_.uuid)


def get_components_from_store(
    store_name: str, mapping: Dict[str, UUIDSourceTuple]
) -> Dict[str, BaseComponent]:
    """Returns a list of components from a store.

    Args:
        store_name: Name of the store.
        mapping: Dict of type str -> UUIDSourceTuple.

    Returns:
        A dict of objects which are a subclass of type BaseComponent.
    """
    store_dir = os.path.join(
        path_utils.get_zenml_config_dir(),
        store_name,
    )
    comps = {}
    for fnames in path_utils.list_dir(store_dir, only_file_names=True):
        uuid = Path(fnames).stem
        key = get_key_from_uuid(UUID(uuid), mapping)
        comps[key] = get_component_from_key(key, mapping)
    return comps
