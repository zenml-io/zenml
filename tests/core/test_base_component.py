#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

from typing import Text

from zenml.core.base_component import BaseComponent


class MockComponent(BaseComponent):
    """Mocking the base component for testing."""

    tmp_path: str

    def get_serialization_dir(self) -> Text:
        """Mock serialization dir"""
        return self.tmp_path


def test_base_component_serialization_logic(tmp_path):
    """Tests the UUID serialization logic of BaseComponent"""

    # Application of the monkeypatch to replace Path.home
    # with the behavior of mockreturn defined above.
    # mc = MockComponent(tmp_path=str(tmp_path))

    # Calling getssh() will use mockreturn in place of Path.home
    # for this test with the monkeypatch.
    # print(mc.get_serialization_dir())
