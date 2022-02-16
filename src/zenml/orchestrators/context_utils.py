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
from typing import TYPE_CHECKING, Any, Dict, Iterator, Tuple

from pydantic import BaseModel

from zenml.enums import MetadataContextTypes
from zenml.logger import get_logger
from zenml.runtime_configuration import RuntimeConfiguration

if TYPE_CHECKING:
    from tfx.proto.orchestration import pipeline_pb2

    from zenml.stack import Stack


logger = get_logger(__name__)


def add_stack_as_metadata_context(
    stack: "Stack",
    context: "pipeline_pb2.ContextSpec",  # type: ignore[valid-type]
) -> None:
    """Given an instance of a stack object, the function adds it to the context
    of a pipeline node in proper format

    Args:
        stack: an instance of a Zenml Stack object
        context: a context proto message within a pipeline node
    """
    # Adding the type of context
    context.type.name = (  # type:ignore[attr-defined]
        MetadataContextTypes.STACK.value
    )

    # Converting the stack into a dict to prepare for hashing
    stack_dict = stack.dict()

    # Setting the name of the context
    name = str(hash(json.dumps(stack_dict, sort_keys=True)))
    context.name.field_value.string_value = name  # type:ignore[attr-defined]

    # Setting the properties of the context
    for k, v in stack_dict.items():
        c_property = context.properties[k]  # type:ignore[attr-defined]
        c_property.field_value.string_value = v


def add_pydantic_object_as_metadata_context(
    obj: "BaseModel",
    context: "pipeline_pb2.ContextSpec",  # type: ignore[valid-type]
    skip_errors: bool = False,
) -> None:
    """
    Add a single Pydantic object to protobuf metadata context.

    Args:
        obj: an instance of a pydantic object
        context: a context proto message within a pipeline node
        skip_errors: silently skip over unserializable fields
    """
    context.type.name = (  # type: ignore[attr-defined]
        obj.__repr_name__().lower()
    )
    # Setting the name of the context
    try:
        name = str(hash(obj.json(sort_keys=True)))
    except TypeError as e:
        class_name = obj.__class__.__name__
        logging.info(
            "Cannot convert %s to json, generating uuid instead. Error: %s",
            class_name,
            e,
        )
        name = f"{class_name}_{uuid.uuid1()}"
    context.name.field_value.string_value = name  # type:ignore[attr-defined]

    # Setting the properties of the context depending on attribute type
    def _serialize(
        dictionary: Dict[str, Any], skip_errors: bool
    ) -> Iterator[Tuple[str, str]]:
        """Itemwise serialize each element in a dictionary."""
        for key, item in dictionary.items():
            try:
                yield key, json.dumps(item)
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

    for key, value in _serialize(obj.dict(), skip_errors=skip_errors):
        c_property = context.properties[key]  # type:ignore[attr-defined]
        c_property.field_value.string_value = value


def add_runtime_configuration_to_node(
    runtime_config: RuntimeConfiguration,
    pipeline_node: Any,
    skip_errors: bool = False,
) -> None:
    """
    Add the runtime configuration of a pipeline run to a protobuf pipeline node.

    Args:
        runtime_config: a ZenML RuntimeConfiguration
        context: a context proto message within a pipeline node
        skip_errors: silently skip over unserializable fields
    """
    for k, v in runtime_config.items():
        if v and issubclass(type(v), BaseModel):
            context = pipeline_node.contexts.contexts.add()
            logger.debug("Adding %s to context", k)
            add_pydantic_object_as_metadata_context(
                context=context, obj=v, skip_errors=skip_errors
            )
