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

from typing import Dict, Optional

from pydantic import BaseModel

from zenml.utils import pydantic_utils


def test_update_model_works():
    """Tests that updating a Pydantic model using our util function works."""

    class TestModel(BaseModel):
        a: int
        b: int

    original = TestModel(a=1, b=2)
    update = TestModel(a=3, b=4)
    updated = pydantic_utils.update_model(original, update)
    assert updated.a == 3
    assert updated.b == 4


def test_update_model_works_for_exclude_unset():
    """Tests that updating a Pydantic model using our util function works."""

    class TestModel(BaseModel):
        a: int
        b: Optional[int] = None

    original = TestModel(a=1, b=2)
    update = TestModel(a=3)
    updated = pydantic_utils.update_model(original, update)
    assert updated.a == 3
    assert updated.b == 2


def test_update_model_works_with_dict():
    """Tests that updating a Pydantic model using our util function works."""

    class TestModel(BaseModel):
        a: int
        b: int

    original = TestModel(a=1, b=2)
    update = {"a": 3, "b": 4}
    updated = pydantic_utils.update_model(original, update)
    assert updated.a == 3
    assert updated.b == 4


def test_update_model_works_recursively():
    """Tests that updating a Pydantic model using our util function works."""

    class TestModel(BaseModel):
        a: int
        b: Dict[str, Dict[str, str]]

    original = TestModel(a=1, b={"c": {"d": "e"}})
    update = TestModel(a=3, b={"c": {"d": "f"}})
    updated = pydantic_utils.update_model(original, update, recursive=True)
    assert updated.a == 3
    assert updated.b["c"]["d"] == "f"


def test_update_model_works_with_dict_none_exclusion():
    """'None' values in the update dictionary get removed if specified."""

    class TestModel(BaseModel):
        a: int
        b: Optional[int] = None

    # Case: when exclude_none is True
    original = TestModel(a=1, b=2)
    update = {"a": 3, "b": None}
    updated = pydantic_utils.update_model(original, update, exclude_none=True)
    assert updated.a == 3
    assert updated.b == 2

    # Case: when exclude_none is False
    original2 = TestModel(a=1, b=2)
    update2 = {"a": 3, "b": None}
    updated2 = pydantic_utils.update_model(
        original2, update2, exclude_none=False
    )
    assert updated2.a == 3
    assert updated2.b is None


def test_update_model_works_with_model_none_exclusion():
    """'None' values in the update model get removed if specified"""

    class TestModel(BaseModel):
        a: int
        b: Optional[int] = None

    # Case: when exclude_none is True
    original = TestModel(a=1, b=2)
    update = TestModel(a=3, b=None)
    updated = pydantic_utils.update_model(original, update, exclude_none=True)
    assert updated.a == 3
    assert updated.b == 2

    # Case: when exclude_none is False
    original2 = TestModel(a=1, b=2)
    update2 = TestModel(a=3, b=None)
    updated2 = pydantic_utils.update_model(
        original2, update2, exclude_none=False
    )
    assert updated2.a == 3
    assert updated2.b is None


def test_template_generator_works():
    """Tests that the template generator works."""

    class ChildTestModel(BaseModel):
        c: int
        d: str

    class TestModel(BaseModel):
        a: int
        b: ChildTestModel

    template = pydantic_utils.TemplateGenerator(TestModel).run()
    assert template == {"a": "int", "b": {"c": "int", "d": "str"}}


def test_yaml_serialization_mixin(tmp_path):
    """Tests that the yaml serialization mixin works."""

    class Model(pydantic_utils.YAMLSerializationMixin):
        b: str
        a: int

    model = Model(a=1, b="b")

    assert model.yaml() == "b: b\na: 1\n"
    assert model.yaml(sort_keys=True) == "a: 1\nb: b\n"

    yaml_path = tmp_path / "test.yaml"
    yaml_path.write_text(model.yaml())

    assert Model.from_yaml(str(yaml_path)) == model
