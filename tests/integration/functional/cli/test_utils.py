#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
from zenml.cli.utils import (
    temporary_active_stack,
)
from zenml.client import Client


def test_temporarily_setting_the_active_stack():
    """Tests the context manager to temporarily activate a stack."""
    initial_stack = Client().active_stack_model
    components = {
        key: components[0].id
        for key, components in initial_stack.components.items()
    }
    new_stack = Client().create_stack(name="new", components=components)

    with temporary_active_stack():
        assert Client().active_stack_model == initial_stack

    with temporary_active_stack(stack_name_or_id=new_stack.id):
        assert Client().active_stack_model == new_stack

    assert Client().active_stack_model == initial_stack
