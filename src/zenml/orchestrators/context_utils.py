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
from typing import TYPE_CHECKING

from pydantic import BaseModel

from zenml.enums import MetadataContextTypes

if TYPE_CHECKING:
    from tfx.proto.orchestration import pipeline_pb2

    from zenml.stack import Stack


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
) -> None:
    """

    Args:
        obj: an instance of a pydantic object
        context: a context proto message within a pipeline node
    """
    context.type.name = (  # type: ignore[attr-defined]
        obj.__repr_name__().lower()
    )
    # Setting the name of the context
    name = str(hash(obj.json(sort_keys=True)))
    context.name.field_value.string_value = name  # type:ignore[attr-defined]

    # Setting the properties of the context
    for k, v in obj.dict().items():
        c_property = context.properties[k]  # type:ignore[attr-defined]
        if isinstance(v, int):
            c_property.field_value.int_value = v
        elif isinstance(v, float):
            c_property.field_value.double_value = v
        elif isinstance(v, str):
            c_property.field_value.string_value = v
        else:
            c_property.field_value.string_value = str(v)
