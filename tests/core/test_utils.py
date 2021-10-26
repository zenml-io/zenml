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


from zenml.core.utils import (
    define_json_config_settings_source,
    generate_customize_sources,
)


def test_define_settings_source_returns_a_callable(tmp_path):
    """Check that define_json_config_settings_source
    returns a callable"""
    config_name = "test_config.json"
    assert callable(define_json_config_settings_source(tmp_path, config_name))


def test_generate_customize_sources_returns_a_callable(tmp_path):
    """Check that generate_customize_sources
    returns a callable"""
    file_name = "test.json"
    assert callable(generate_customize_sources(tmp_path, file_name))
