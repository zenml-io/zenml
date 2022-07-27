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

import uuid
from contextlib import ExitStack as does_not_raise

import pytest

from zenml.secrets_managers.base_secrets_manager import SecretsManagerScope
from zenml.secrets_managers.local.local_secrets_manager import (
    LocalSecretsManager,
)


def test_scope_defaults_to_component():
    """Tests that secrets managers are component-scoped by default."""
    secrets_manager = LocalSecretsManager(name="")
    assert secrets_manager.scope == SecretsManagerScope.COMPONENT


def test_scope_backwards_compatibility():
    """Tests that existing secrets managers are unscoped by default."""
    secrets_manager_dict = dict(
        uuid=uuid.uuid4(),
        name="local_test",
        secrets_file="/tmp/local_test",
    )
    secrets_manager = LocalSecretsManager(**secrets_manager_dict)
    assert secrets_manager.scope == SecretsManagerScope.NONE
    assert secrets_manager.namespace is None


def test_scope_namespace_required():
    """Tests that namespace scoped secrets managers need a namespace."""
    with pytest.raises(ValueError):
        LocalSecretsManager(name="", scope=SecretsManagerScope.NAMESPACE)
    with does_not_raise():
        LocalSecretsManager(
            name="", scope=SecretsManagerScope.NAMESPACE, namespace="alpha"
        )
