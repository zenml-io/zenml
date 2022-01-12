#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from contextlib import ExitStack as does_not_raise

import pytest


def test_stack_component_default_method_implementations(mock_component_class):
    """Tests the return values for default implementations of some
    StackComponent methods."""
    component = mock_component_class()

    assert component.validator is None
    assert component.log_file is None
    assert component.runtime_options == {}
    assert component.requirements == []

    assert component.is_provisioned is False
    assert component.is_running is False

    with pytest.raises(NotImplementedError):
        component.provision()

    with pytest.raises(NotImplementedError):
        component.deprovision()

    with pytest.raises(NotImplementedError):
        component.resume()

    with pytest.raises(NotImplementedError):
        component.suspend()


def test_stack_component_dict_only_contains_public_attributes(
    mock_component_class,
):
    """Tests that the `dict()` method which is used to serialize stack
    components does not include private attributes."""
    component = mock_component_class()
    assert component._some_private_attribute_name == "Also Aria"

    expected_dict_keys = {"some_public_attribute_name", "name", "uuid"}
    assert component.dict().keys() == expected_dict_keys


def test_stack_component_public_attributes_are_immutable(mock_component_class):
    """Tests that stack component public attributes are immutable but private
    attribute can be modified."""
    component = mock_component_class()

    with pytest.raises(TypeError):
        component.some_public_attribute_name = "Not Aria"

    with does_not_raise():
        component._some_private_attribute_name = "Woof"
