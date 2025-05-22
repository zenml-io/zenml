#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

from zenml.utils import yaml_utils


def test_is_yaml_detects_yaml_extensions() -> None:
    """Test detection of YAML file extensions."""
    assert yaml_utils.is_yaml("config.yaml")
    assert yaml_utils.is_yaml("config.yml")


def test_is_yaml_returns_false_for_other_extensions() -> None:
    """Test that non-YAML extensions return ``False``."""
    assert not yaml_utils.is_yaml("config.txt")
    assert not yaml_utils.is_yaml("notyaml")
