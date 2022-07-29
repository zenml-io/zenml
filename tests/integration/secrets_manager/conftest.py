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

from tests.integration.secrets_manager.utils import get_secrets_manager
from zenml.secrets_managers.base_secrets_manager import SecretsManagerScope
from zenml.utils.string_utils import random_str


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "secret_scoping: mark Secrets Manager tests that test secret scoping",
    )


def pytest_collection_modifyitems(config, items):
    flavor = config.getoption("secrets_manager_flavor")
    if flavor in ["local"]:
        # skip scope testing with secrets manager that don't understand scoping
        skip_scope = pytest.mark.skip(
            reason=f"{flavor} Secrets Manager Does not support scoping"
        )
        for item in items:
            if "secret_scoping" in item.keywords:
                item.add_marker(skip_scope)


@pytest.fixture(scope="function")
def unscoped_secrets_manager(request: pytest.FixtureRequest):
    """Fixture to yield an unscoped secrets manager."""
    secrets_manager = get_secrets_manager(
        request,
        name=f"zenml_pytest_{random_str(16).lower()}",
        scope=SecretsManagerScope.NONE,
    )
    old_secrets = secrets_manager.get_all_secret_keys()
    yield secrets_manager
    new_secrets = secrets_manager.get_all_secret_keys()
    for secret in set(new_secrets) - set(old_secrets):
        secrets_manager.delete_secret(secret)


@pytest.fixture(scope="function")
def global_scoped_secrets_manager(request: pytest.FixtureRequest):
    """Fixture to yield a global scoped secrets manager."""
    secrets_manager = get_secrets_manager(
        request,
        name=f"zenml_pytest_{random_str(16).lower()}",
        scope=SecretsManagerScope.GLOBAL,
    )
    old_secrets = secrets_manager.get_all_secret_keys()
    yield secrets_manager
    new_secrets = secrets_manager.get_all_secret_keys()
    for secret in set(new_secrets) - set(old_secrets):
        secrets_manager.delete_secret(secret)


@pytest.fixture(scope="function")
def component_scoped_secrets_manager(request: pytest.FixtureRequest):
    """Fixture to yield a component scoped secrets manager."""
    secrets_manager = get_secrets_manager(
        request,
        name=f"zenml_pytest_{random_str(16).lower()}",
        scope=SecretsManagerScope.COMPONENT,
    )
    old_secrets = secrets_manager.get_all_secret_keys()
    yield secrets_manager
    new_secrets = secrets_manager.get_all_secret_keys()
    for secret in set(new_secrets) - set(old_secrets):
        secrets_manager.delete_secret(secret)


@pytest.fixture(scope="function")
def namespace_scoped_secrets_manager(request: pytest.FixtureRequest):
    """Fixture to yield a namespace scoped secrets manager."""
    secrets_manager = get_secrets_manager(
        request,
        name=f"zenml_pytest_{random_str(16).lower()}",
        scope=SecretsManagerScope.NAMESPACE,
        namespace=f"pytest_{random_str(8).lower()}",
    )
    old_secrets = secrets_manager.get_all_secret_keys()
    yield secrets_manager
    new_secrets = secrets_manager.get_all_secret_keys()
    for secret in set(new_secrets) - set(old_secrets):
        secrets_manager.delete_secret(secret)


@pytest.fixture(scope="function")
def secrets_manager(request: pytest.FixtureRequest):
    secrets_manager = get_secrets_manager(
        request,
        name=f"zenml_pytest_{random_str(16).lower()}",
        scope=request.param,
        namespace=f"pytest_{random_str(8).lower()}",
    )
    old_secrets = secrets_manager.get_all_secret_keys()
    yield secrets_manager
    new_secrets = secrets_manager.get_all_secret_keys()
    for secret in set(new_secrets) - set(old_secrets):
        secrets_manager.delete_secret(secret)
