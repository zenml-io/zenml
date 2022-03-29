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

import datetime as dt
from typing import Optional

import pytest
from pydantic.main import BaseModel
from tfx.proto.orchestration.pipeline_pb2 import PipelineNode

from zenml.enums import MetadataContextTypes, StackComponentType
from zenml.orchestrators.context_utils import add_runtime_configuration_to_node
from zenml.repository import Repository
from zenml.steps import step


def test_pipeline_storing_stack_in_the_metadata_store(one_step_pipeline):
    """Tests that returning an object of a type that wasn't specified (either
    directly or as part of the `Output` tuple annotation) raises an error."""

    @step
    def some_step_1() -> int:
        return 3

    pipeline_ = one_step_pipeline(some_step_1())
    pipeline_.run()

    repo = Repository()

    stack = repo.get_stack(repo.active_stack_name)
    metadata_store = stack.metadata_store
    stack_contexts = metadata_store.store.get_contexts_by_type(
        MetadataContextTypes.STACK.value
    )

    assert len(stack_contexts) == 1

    assert stack_contexts[0].custom_properties[
        StackComponentType.ORCHESTRATOR.value
    ].string_value == stack.orchestrator.json(sort_keys=True)
    assert stack_contexts[0].custom_properties[
        StackComponentType.ARTIFACT_STORE.value
    ].string_value == stack.artifact_store.json(sort_keys=True)
    assert stack_contexts[0].custom_properties[
        StackComponentType.METADATA_STORE.value
    ].string_value == stack.metadata_store.json(sort_keys=True)


def test_pydantic_object_to_metadata_context():
    class Unjsonable:
        def __init__(self):
            self.value = "value"

    class StringAttributes(BaseModel):
        b: str
        a: str

    class DateTimeAttributes(BaseModel):
        t: dt.datetime
        d: Optional[dt.date]

    class MixedAttributes(BaseModel):
        class Config:
            arbitrary_types_allowed = True

        s: str
        f: float
        i: int
        b: bool
        l: list
        u: Unjsonable

    # straight-forward fully serializable object

    node1 = PipelineNode()
    obj1 = StringAttributes(b="bob", a="alice")
    add_runtime_configuration_to_node(node1, {"key": obj1})
    print(f"methods: {dir(node1.contexts.contexts)}")
    ctx1 = node1.contexts.contexts[0]
    assert ctx1.type.name == "stringattributes"
    assert ctx1.name.field_value.string_value == str(
        hash('{"a": "alice", "b": "bob"}')
    )

    # object with serialization difficulties
    obj2 = MixedAttributes(
        s="steve", f=3.14, i=42, b=True, l=[1, 2], u=Unjsonable()
    )

    node2 = PipelineNode()
    add_runtime_configuration_to_node(
        node2, dict(k=obj2, ignore_unserializable_fields=True)
    )
    ctx2 = node2.contexts.contexts[0]
    assert ctx2.type.name == "mixedattributes"
    assert ctx2.name.field_value.string_value.startswith("MixedAttributes")
    assert "s" in ctx2.properties.keys()
    assert ctx2.properties.get("b").field_value.string_value == "true"
    assert ctx2.properties.get("l").field_value.string_value == "[1, 2]"
    assert "u" not in ctx2.properties.keys()

    node3 = PipelineNode()
    with pytest.raises(TypeError):
        add_runtime_configuration_to_node(node3, {"k": obj2})

    # use pydantics serialization magic

    obj4 = DateTimeAttributes(
        t=dt.datetime(2022, 10, 20, 16, 42, 5), d=dt.date(2012, 12, 20)
    )
    node4 = PipelineNode()
    add_runtime_configuration_to_node(node4, dict(k=obj4))
    ctx4 = node4.contexts.contexts[0]
    assert ctx4.type.name == "datetimeattributes"
    assert ctx4.properties.get("d").field_value.string_value == '"2012-12-20"'
    assert (
        ctx4.properties.get("t").field_value.string_value
        == '"2022-10-20T16:42:05"'
    )
