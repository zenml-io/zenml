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
import pytest

from tests.integration.functional.secrets_manager.utils import (
    secrets_manager_session,
)
from zenml.secrets_managers.base_secrets_manager import SecretsManagerScope
from zenml.utils.string_utils import random_str


@pytest.fixture(scope="function")
def default_secrets_manager(request: pytest.FixtureRequest):
    """Fixture to yield a default secrets manager."""
    with secrets_manager_session(
        request,
        name=f"zenml_pytest_{random_str(16).lower()}",
    ) as secrets_manager:
        old_secrets = secrets_manager.get_all_secret_keys()
        yield secrets_manager
        new_secrets = secrets_manager.get_all_secret_keys()
        for secret in set(new_secrets) - set(old_secrets):
            secrets_manager.delete_secret(secret)


@pytest.fixture(scope="function")
def unscoped_secrets_manager(request: pytest.FixtureRequest):
    """Fixture to yield an unscoped secrets manager."""
    with secrets_manager_session(
        request,
        name=f"zenml_pytest_{random_str(16).lower()}",
        scope=SecretsManagerScope.NONE,
    ) as secrets_manager:
        old_secrets = secrets_manager.get_all_secret_keys()
        yield secrets_manager
        new_secrets = secrets_manager.get_all_secret_keys()
        for secret in set(new_secrets) - set(old_secrets):
            secrets_manager.delete_secret(secret)


@pytest.fixture(scope="function")
def global_scoped_secrets_manager(request: pytest.FixtureRequest):
    """Fixture to yield a global scoped secrets manager."""
    with secrets_manager_session(
        request,
        name=f"zenml_pytest_{random_str(16).lower()}",
        scope=SecretsManagerScope.GLOBAL,
    ) as secrets_manager:
        old_secrets = secrets_manager.get_all_secret_keys()
        yield secrets_manager
        new_secrets = secrets_manager.get_all_secret_keys()
        for secret in set(new_secrets) - set(old_secrets):
            secrets_manager.delete_secret(secret)


@pytest.fixture(scope="function")
def component_scoped_secrets_manager(request: pytest.FixtureRequest):
    """Fixture to yield a component scoped secrets manager."""
    with secrets_manager_session(
        request,
        name=f"zenml_pytest_{random_str(16).lower()}",
        scope=SecretsManagerScope.COMPONENT,
    ) as secrets_manager:
        old_secrets = secrets_manager.get_all_secret_keys()
        yield secrets_manager
        new_secrets = secrets_manager.get_all_secret_keys()
        for secret in set(new_secrets) - set(old_secrets):
            secrets_manager.delete_secret(secret)


@pytest.fixture(scope="function")
def namespace_scoped_secrets_manager(request: pytest.FixtureRequest):
    """Fixture to yield a namespace scoped secrets manager."""
    with secrets_manager_session(
        request,
        name=f"zenml_pytest_{random_str(16).lower()}",
        scope=SecretsManagerScope.NAMESPACE,
        namespace=f"pytest{random_str(8).lower()}",
    ) as secrets_manager:
        old_secrets = secrets_manager.get_all_secret_keys()
        yield secrets_manager
        new_secrets = secrets_manager.get_all_secret_keys()
        for secret in set(new_secrets) - set(old_secrets):
            secrets_manager.delete_secret(secret)


@pytest.fixture(scope="function")
def secrets_manager(request: pytest.FixtureRequest):
    with secrets_manager_session(
        request,
        name=f"zenml_pytest_{random_str(16).lower()}",
        scope=request.param,
        namespace=f"pytest{random_str(8).lower()}",
    ) as secrets_manager:
        old_secrets = secrets_manager.get_all_secret_keys()
        yield secrets_manager
        new_secrets = secrets_manager.get_all_secret_keys()
        for secret in set(new_secrets) - set(old_secrets):
            secrets_manager.delete_secret(secret)
