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
import json
import logging
import uuid
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterator, Tuple, cast

from pydantic import BaseModel

from zenml.logger import get_logger
from zenml.runtime_configuration import RuntimeConfiguration

if TYPE_CHECKING:
    from tfx.proto.orchestration import pipeline_pb2


logger = get_logger(__name__)


def add_context_to_node(
    pipeline_node: "pipeline_pb2.PipelineNode",
    type_: str,
    name: str,
    properties: Dict[str, str],
) -> None:
    """
    Add a new context to a TFX protobuf pipeline node.

    Args:
        pipeline_node: A tfx protobuf pipeline node
        type_: The type name for the context to be added
        name: Unique key for the context
        properties: dictionary of strings as properties of the context
    """
    # Add a new context to the pipeline
    context: "pipeline_pb2.ContextSpec" = pipeline_node.contexts.contexts.add()
    # Adding the type of context
    context.type.name = type_
    # Setting the name of the context
    context.name.field_value.string_value = name
    # Setting the properties of the context depending on attribute type
    for key, value in properties.items():
        c_property = context.properties[key]
        c_property.field_value.string_value = value


def serialize_pydantic_object(
    obj: BaseModel, *, skip_errors: bool = False
) -> Dict[str, str]:
    """Convert a pydantic object to a dict of strings"""

    class PydanticEncoder(json.JSONEncoder):
        def default(self, o: Any) -> Any:
            try:
                return cast(Callable[[Any], str], obj.__json_encoder__)(o)
            except TypeError:
                return super().default(o)

    def _inner_generator(
        dictionary: Dict[str, Any]
    ) -> Iterator[Tuple[str, str]]:
        """Itemwise serialize each element in a dictionary."""
        for key, item in dictionary.items():
            try:
                yield key, json.dumps(item, cls=PydanticEncoder)
            except TypeError as e:
                if skip_errors:
                    logging.info(
                        "Skipping adding field '%s' to metadata context as "
                        "it cannot be serialized due to %s.",
                        key,
                        e,
                    )
                else:
                    raise TypeError(
                        f"Invalid type {type(item)} for key {key} can not be "
                        "serialized."
                    ) from e

    return {key: value for key, value in _inner_generator(obj.dict())}


def add_runtime_configuration_to_node(
    pipeline_node: "pipeline_pb2.PipelineNode",
    runtime_config: RuntimeConfiguration,
) -> None:
    """
    Add the runtime configuration of a pipeline run to a protobuf pipeline node.

    Args:
        pipeline_node: a tfx protobuf pipeline node
        runtime_config: a ZenML RuntimeConfiguration
    """
    skip_errors: bool = runtime_config.get(
        "ignore_unserializable_fields", False
    )

    # Determine the name of the context
    def _name(obj: "BaseModel") -> str:
        """Compute a unique context name for a pydantic BaseModel."""
        try:
            return str(hash(obj.json(sort_keys=True)))
        except TypeError as e:
            class_name = obj.__class__.__name__
            logging.info(
                "Cannot convert %s to json, generating uuid instead. Error: %s",
                class_name,
                e,
            )
            return f"{class_name}_{uuid.uuid1()}"

    # iterate over all attributes of runtime context, serializing all pydantic
    # objects to node context.
    for key, obj in runtime_config.items():
        if isinstance(obj, BaseModel):
            logger.debug("Adding %s to context", key)
            add_context_to_node(
                pipeline_node,
                type_=obj.__repr_name__().lower(),
                name=_name(obj),
                properties=serialize_pydantic_object(
                    obj, skip_errors=skip_errors
                ),
            )
