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
from contextlib import ExitStack as does_not_raise

import pytest


def test_stack_component_default_method_implementations(stub_component):
    """Tests the return values for default implementations of some
    StackComponent methods."""
    assert stub_component.validator is None
    assert stub_component.log_file is None
    assert stub_component.runtime_options == {}
    assert stub_component.requirements == set()

    assert stub_component.is_provisioned is True
    assert stub_component.is_running is True

    with pytest.raises(NotImplementedError):
        stub_component.provision()

    with pytest.raises(NotImplementedError):
        stub_component.deprovision()

    with pytest.raises(NotImplementedError):
        stub_component.resume()

    with pytest.raises(NotImplementedError):
        stub_component.suspend()


def test_stack_component_dict_only_contains_public_attributes(
    stub_component,
):
    """Tests that the `dict()` method which is used to serialize stack
    components does not include private attributes."""
    assert stub_component._some_private_attribute_name == "Also Aria"

    expected_dict_keys = {"some_public_attribute_name", "name", "uuid"}
    assert stub_component.dict().keys() == expected_dict_keys


def test_stack_component_public_attributes_are_immutable(stub_component):
    """Tests that stack component public attributes are immutable but private
    attribute can be modified."""
    with pytest.raises(TypeError):
        stub_component.some_public_attribute_name = "Not Aria"

    with does_not_raise():
        stub_component._some_private_attribute_name = "Woof"
