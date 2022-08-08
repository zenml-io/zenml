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

from zenml.secrets_managers import BaseSecretsManager


class StubSecretsManager(BaseSecretsManager):
    attribute: str
    FLAVOR = "TEST"

    def get_secret(self):
        pass

    def register_secret(self):
        pass

    def update_secret(self):
        pass

    def get_all_secret_keys(self):
        pass

    def delete_secret(self):
        pass

    def delete_all_secrets(self):
        pass


def test_base_secrets_manager_prevents_secret_references():
    """Tests that the secrets manager prevents all secret references"""

    with pytest.raises(ValueError):
        StubSecretsManager(name="", attribute="{{secret.key}}")

    with does_not_raise():
        StubSecretsManager(name="", attribute="not_a_secret_ref")
