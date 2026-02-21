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

from zenml.utils import settings_utils


def test_sandbox_setting_keys_are_valid():
    """Tests that sandbox setting keys are accepted by validation helpers."""
    assert settings_utils.is_stack_component_setting_key("sandbox")
    assert settings_utils.is_stack_component_setting_key("sandbox.modal")
    assert settings_utils.is_valid_setting_key("sandbox.modal")
