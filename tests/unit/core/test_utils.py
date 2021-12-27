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

import json

from pydantic import BaseSettings

from zenml.core.utils import (
    define_json_config_settings_source,
    generate_customise_sources,
)


def test_define_settings_source_returns_a_callable(tmp_path: str) -> None:
    """Check that define_json_config_settings_source
    returns a callable"""
    config_name = "test_config.json"
    assert callable(define_json_config_settings_source(tmp_path, config_name))


def test_generate_customise_sources_returns_a_class_method(
    tmp_path: str,
) -> None:
    """Check that generate_customise_sources
    returns a callable"""
    file_name = "test.json"
    assert isinstance(
        generate_customise_sources(tmp_path, file_name), classmethod
    )


def test_json_config_settings_source_returns_a_dict(tmp_path: str) -> None:
    """Check that define_json_config_settings_source
    returns a dict"""
    config_name = "test_config.json"
    settings_source = define_json_config_settings_source(tmp_path, config_name)
    some_data = {"some": "data"}
    with open(tmp_path / config_name, "w") as json_file:
        json.dump(some_data, json_file)
    assert isinstance(settings_source(BaseSettings), dict)
    assert settings_source(BaseSettings) == some_data
