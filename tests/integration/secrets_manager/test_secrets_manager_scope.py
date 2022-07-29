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
import time
import uuid
from contextlib import ExitStack as does_not_raise
from typing import Any, Dict

import pytest

from tests.integration.secrets_manager.utils import (
    get_arbitrary_secret,
    get_secrets_manager,
)
from zenml.secret.arbitrary_secret_schema import ArbitrarySecretSchema
from zenml.secrets_managers.base_secrets_manager import (
    BaseSecretsManager,
    SecretsManagerScope,
)


@pytest.mark.secret_scoping
def test_scope_defaults_to_component(request: pytest.FixtureRequest):
    """Tests that secrets managers are component-scoped by default."""
    secrets_manager = get_secrets_manager(request)
    assert secrets_manager.scope == SecretsManagerScope.COMPONENT


def test_scope_backwards_compatibility(request: pytest.FixtureRequest):
    """Tests the default scope of existing secrets managers."""
    secrets_manager = get_secrets_manager(request, uuid=uuid.uuid4())
    assert secrets_manager.scope == SecretsManagerScope.NONE
    assert secrets_manager.namespace is None

    with does_not_raise():
        secrets_manager = get_secrets_manager(
            request, uuid=uuid.uuid4(), scope=SecretsManagerScope.NONE
        )
    assert secrets_manager.scope == SecretsManagerScope.NONE


@pytest.mark.secret_scoping
def test_scope_namespace_required(request: pytest.FixtureRequest):
    """Tests that namespace scoped secrets managers need a namespace."""
    with pytest.raises(ValueError):
        get_secrets_manager(request, scope=SecretsManagerScope.NAMESPACE)
    with does_not_raise():
        get_secrets_manager(
            request, scope=SecretsManagerScope.NAMESPACE, namespace="alpha"
        )


@pytest.mark.secret_scoping
def test_same_secret_different_scopes(
    unscoped_secrets_manager: BaseSecretsManager,
    global_scoped_secrets_manager: BaseSecretsManager,
    component_scoped_secrets_manager: BaseSecretsManager,
    namespace_scoped_secrets_manager: BaseSecretsManager,
):
    """Tests that secrets managers with different scopes do not share secrets."""
    component_secrets = component_scoped_secrets_manager.get_all_secret_keys()
    assert len(component_secrets) == 0

    namespace_secrets = namespace_scoped_secrets_manager.get_all_secret_keys()
    assert len(namespace_secrets) == 0

    unscoped_secret = get_arbitrary_secret()
    unscoped_secrets_manager.register_secret(unscoped_secret)
    global_secret = get_arbitrary_secret(unscoped_secret.name)
    with does_not_raise():
        global_scoped_secrets_manager.register_secret(global_secret)
    component_secret = get_arbitrary_secret(unscoped_secret.name)
    with does_not_raise():
        component_scoped_secrets_manager.register_secret(component_secret)
    namespace_secret = get_arbitrary_secret(unscoped_secret.name)
    with does_not_raise():
        namespace_scoped_secrets_manager.register_secret(namespace_secret)

    # AWS can take some time to make the secrets operationally available
    time.sleep(5)

    with does_not_raise():
        secret = unscoped_secrets_manager.get_secret(unscoped_secret.name)
    assert isinstance(secret, ArbitrarySecretSchema)
    assert secret.arbitrary_kv_pairs == unscoped_secret.arbitrary_kv_pairs

    with does_not_raise():
        secret = global_scoped_secrets_manager.get_secret(unscoped_secret.name)
    assert isinstance(secret, ArbitrarySecretSchema)
    assert secret.arbitrary_kv_pairs == global_secret.arbitrary_kv_pairs

    with does_not_raise():
        secret = component_scoped_secrets_manager.get_secret(
            unscoped_secret.name
        )
    assert isinstance(secret, ArbitrarySecretSchema)
    assert secret.arbitrary_kv_pairs == component_secret.arbitrary_kv_pairs

    with does_not_raise():
        secret = namespace_scoped_secrets_manager.get_secret(
            unscoped_secret.name
        )
    assert isinstance(secret, ArbitrarySecretSchema)
    assert secret.arbitrary_kv_pairs == namespace_secret.arbitrary_kv_pairs

    unscoped_secrets = unscoped_secrets_manager.get_all_secret_keys()
    assert len(unscoped_secrets) >= 1
    assert unscoped_secret.name in unscoped_secrets

    global_secrets = global_scoped_secrets_manager.get_all_secret_keys()
    assert len(global_secrets) >= 1
    assert global_secret.name in global_secrets

    component_secrets = component_scoped_secrets_manager.get_all_secret_keys()
    assert len(component_secrets) == 1
    assert component_secret.name in component_secrets

    namespace_secrets = namespace_scoped_secrets_manager.get_all_secret_keys()
    assert len(namespace_secrets) == 1
    assert namespace_secret.name in namespace_secrets


@pytest.mark.secret_scoping
def test_different_secret_different_scopes(
    unscoped_secrets_manager: BaseSecretsManager,
    global_scoped_secrets_manager: BaseSecretsManager,
    component_scoped_secrets_manager: BaseSecretsManager,
    namespace_scoped_secrets_manager: BaseSecretsManager,
):
    """Tests that secrets managers with different scopes do not share secrets."""
    component_secrets = component_scoped_secrets_manager.get_all_secret_keys()
    assert len(component_secrets) == 0

    namespace_secrets = namespace_scoped_secrets_manager.get_all_secret_keys()
    assert len(namespace_secrets) == 0

    unscoped_secret = get_arbitrary_secret()
    unscoped_secrets_manager.register_secret(unscoped_secret)
    global_secret = get_arbitrary_secret()
    with does_not_raise():
        global_scoped_secrets_manager.register_secret(global_secret)
    component_secret = get_arbitrary_secret()
    with does_not_raise():
        component_scoped_secrets_manager.register_secret(component_secret)
    namespace_secret = get_arbitrary_secret()
    with does_not_raise():
        namespace_scoped_secrets_manager.register_secret(namespace_secret)

    # AWS can take some time to make the secrets operationally available
    time.sleep(5)

    with does_not_raise():
        secret = unscoped_secrets_manager.get_secret(unscoped_secret.name)
    assert isinstance(secret, ArbitrarySecretSchema)
    assert secret.arbitrary_kv_pairs == unscoped_secret.arbitrary_kv_pairs
    with pytest.raises(KeyError):
        unscoped_secrets_manager.get_secret(global_secret.name)
    with pytest.raises(KeyError):
        unscoped_secrets_manager.get_secret(component_secret.name)
    with pytest.raises(KeyError):
        unscoped_secrets_manager.get_secret(namespace_secret.name)

    with does_not_raise():
        secret = global_scoped_secrets_manager.get_secret(global_secret.name)
    assert isinstance(secret, ArbitrarySecretSchema)
    assert secret.arbitrary_kv_pairs == global_secret.arbitrary_kv_pairs
    with pytest.raises(KeyError):
        global_scoped_secrets_manager.get_secret(unscoped_secret.name)
    with pytest.raises(KeyError):
        global_scoped_secrets_manager.get_secret(component_secret.name)
    with pytest.raises(KeyError):
        global_scoped_secrets_manager.get_secret(namespace_secret.name)

    with does_not_raise():
        secret = component_scoped_secrets_manager.get_secret(
            component_secret.name
        )
    assert isinstance(secret, ArbitrarySecretSchema)
    assert secret.arbitrary_kv_pairs == component_secret.arbitrary_kv_pairs
    with pytest.raises(KeyError):
        component_scoped_secrets_manager.get_secret(unscoped_secret.name)
    with pytest.raises(KeyError):
        component_scoped_secrets_manager.get_secret(global_secret.name)
    with pytest.raises(KeyError):
        component_scoped_secrets_manager.get_secret(namespace_secret.name)

    with does_not_raise():
        secret = namespace_scoped_secrets_manager.get_secret(
            namespace_secret.name
        )
    assert isinstance(secret, ArbitrarySecretSchema)
    assert secret.arbitrary_kv_pairs == namespace_secret.arbitrary_kv_pairs
    with pytest.raises(KeyError):
        namespace_scoped_secrets_manager.get_secret(unscoped_secret.name)
    with pytest.raises(KeyError):
        namespace_scoped_secrets_manager.get_secret(global_secret.name)
    with pytest.raises(KeyError):
        namespace_scoped_secrets_manager.get_secret(component_secret.name)

    unscoped_secrets = unscoped_secrets_manager.get_all_secret_keys()
    assert len(unscoped_secrets) >= 1
    assert unscoped_secret.name in unscoped_secrets
    assert global_secret.name not in unscoped_secrets
    assert component_secret.name not in unscoped_secrets
    assert namespace_secret.name not in unscoped_secrets

    global_secrets = global_scoped_secrets_manager.get_all_secret_keys()
    assert len(global_secrets) >= 1
    assert global_secret.name in global_secrets
    assert unscoped_secret.name not in global_secrets
    assert component_secret.name not in global_secrets
    assert namespace_secret.name not in global_secrets

    component_secrets = component_scoped_secrets_manager.get_all_secret_keys()
    assert len(component_secrets) == 1
    assert component_secret.name in component_secrets

    namespace_secrets = namespace_scoped_secrets_manager.get_all_secret_keys()
    assert len(namespace_secrets) == 1
    assert namespace_secret.name in namespace_secrets


@pytest.mark.secret_scoping
@pytest.mark.parametrize(
    "secrets_manager",
    SecretsManagerScope.values(),
    indirect=True,
)
def test_secrets_shared_at_scope_level(
    secrets_manager: BaseSecretsManager,
    request: pytest.FixtureRequest,
):
    """Tests that secrets managers share secrets if they are in the same scope.

    This test uses two instances of Secrets Manager in the same scope to verify
    that the secrets added, updated and deleted in one instance are immediately
    visible in the second instance.
    """
    copy_kwargs: Dict[str, Any] = dict(
        scope=secrets_manager.scope,
        namespace=secrets_manager.namespace,
    )
    # two secrets managers using component scope also have to share the UUID
    # value to be in the same scope
    if secrets_manager.scope == SecretsManagerScope.COMPONENT:
        copy_kwargs["uuid"] = secrets_manager.uuid

    another_secrets_manager = get_secrets_manager(request, **copy_kwargs)

    secret = get_arbitrary_secret()

    with pytest.raises(KeyError):
        secrets_manager.get_secret(secret.name)
    with pytest.raises(KeyError):
        another_secrets_manager.get_secret(secret.name)

    # add a secret
    secrets_manager.register_secret(secret)

    if secrets_manager.FLAVOR == "aws":
        # AWS can take some time to make the secrets operationally available
        time.sleep(5)

    with does_not_raise():
        secrets_manager.get_secret(secret.name)
    with does_not_raise():
        other_secret = another_secrets_manager.get_secret(secret.name)

    assert isinstance(other_secret, ArbitrarySecretSchema)
    assert other_secret.arbitrary_kv_pairs == secret.arbitrary_kv_pairs

    available_secrets = secrets_manager.get_all_secret_keys()
    assert len(available_secrets) >= 1
    assert secret.name in available_secrets

    other_available_secrets = another_secrets_manager.get_all_secret_keys()
    assert len(other_available_secrets) >= 1
    assert secret.name in other_available_secrets

    # update the secret
    new_secret = get_arbitrary_secret(name=secret.name)

    # TODO: the current GCP Secrets Manager implementation has a bug in it
    # that prevents new keys from being added to an existing secret. We could
    # fix it, but given that unscoped secrets are deprecated, it's better to
    # just wait until it is phased out.
    if secrets_manager.FLAVOR == "gcp_secrets_manager":
        new_secret.arbitrary_kv_pairs = secret.arbitrary_kv_pairs.copy()
        new_secret.arbitrary_kv_pairs[
            list(new_secret.arbitrary_kv_pairs.keys())[0]
        ] = "new_value"
    secrets_manager.update_secret(new_secret)

    with does_not_raise():
        other_secret = another_secrets_manager.get_secret(secret.name)

    assert isinstance(other_secret, ArbitrarySecretSchema)
    assert other_secret.arbitrary_kv_pairs != secret.arbitrary_kv_pairs
    assert other_secret.arbitrary_kv_pairs == new_secret.arbitrary_kv_pairs

    # delete the secret
    secrets_manager.delete_secret(secret.name)

    if secrets_manager.FLAVOR == "aws":
        # AWS can take some time to delete the secrets
        time.sleep(10)

    with pytest.raises(KeyError):
        secrets_manager.get_secret(secret.name)
    with pytest.raises(KeyError):
        another_secrets_manager.get_secret(secret.name)

    available_secrets = secrets_manager.get_all_secret_keys()
    assert secret.name not in available_secrets

    other_available_secrets = another_secrets_manager.get_all_secret_keys()
    assert secret.name not in other_available_secrets


@pytest.mark.secret_scoping
@pytest.mark.parametrize(
    "secrets_manager",
    [SecretsManagerScope.COMPONENT, SecretsManagerScope.NAMESPACE],
    indirect=True,
)
def test_secrets_not_shared_in_different_scopes(
    secrets_manager: BaseSecretsManager,
    request: pytest.FixtureRequest,
):
    """Tests that secrets managers do not share secrets if they are in different scopes.

    This test uses two instances of Secrets Manager in different scopes to verify
    that the secrets added, updated and deleted in one instance are not
    visible in the second instance.
    """
    other_namespace = secrets_manager.namespace
    if other_namespace:
        other_namespace = other_namespace[::-1]

    another_secrets_manager = get_secrets_manager(
        request,
        scope=secrets_manager.scope,
        namespace=other_namespace,
    )

    secret = get_arbitrary_secret()

    with pytest.raises(KeyError):
        secrets_manager.get_secret(secret.name)
    with pytest.raises(KeyError):
        another_secrets_manager.get_secret(secret.name)

    # add a secret
    secrets_manager.register_secret(secret)

    if secrets_manager.FLAVOR == "aws":
        # AWS can take some time to make the secrets operationally available
        time.sleep(5)

    with does_not_raise():
        secrets_manager.get_secret(secret.name)
    with pytest.raises(KeyError):
        another_secrets_manager.get_secret(secret.name)

    available_secrets = secrets_manager.get_all_secret_keys()
    assert len(available_secrets) == 1
    assert secret.name in available_secrets

    other_available_secrets = another_secrets_manager.get_all_secret_keys()
    assert len(other_available_secrets) == 0
