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


from zenml.config.base_settings import BaseSettings, ConfigurationLevel
from zenml.config.secret_reference_mixin import SecretReferenceMixin


def test_base_settings_default_configuration_level():
    """Tests that by default settings can be specified on both a pipeline
    and a step."""
    assert ConfigurationLevel.STEP in BaseSettings.LEVEL
    assert ConfigurationLevel.PIPELINE in BaseSettings.LEVEL


def test_base_settings_inherit_from_secret_reference_mixin():
    """Tests that the BaseSettings class inherits from the SecretReferenceMixin
    class so that its string attributes can be specified as secret references.
    """
    assert issubclass(BaseSettings, SecretReferenceMixin)
