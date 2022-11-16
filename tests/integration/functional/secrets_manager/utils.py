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
import logging
from contextlib import contextmanager
from typing import Any, Generator, Optional, cast

import pytest

from tests.harness.harness import TestHarness
from zenml.client import Client
from zenml.enums import StackComponentType
from zenml.secret.arbitrary_secret_schema import ArbitrarySecretSchema
from zenml.secrets_managers.base_secrets_manager import BaseSecretsManager
from zenml.stack import StackComponent
from zenml.utils.string_utils import random_str


@contextmanager
def secrets_manager_session(
    request: pytest.FixtureRequest,
    **kwargs: Any,
) -> Generator[BaseSecretsManager, None, None]:
    """Utility function to create secrets managers of different scopes.

    This function is used to instantiate Secrets Managers of different scopes
    to use in integration testing. The secret manager mandated or tracked by
    the current test environment is used as a template.

    Args:
        request: The pytest request object.
        **kwargs: Keyword arguments to pass to the secrets manager.

    Yields:
        A secrets manager of the specified scope.
    """
    harness = TestHarness()
    env = harness.active_environment

    no_cleanup = request.config.getoption("no_cleanup", False)

    mandatory_secrets_managers = env.mandatory_components.get(
        StackComponentType.SECRETS_MANAGER, []
    )
    optional_secrets_managers = env.optional_components.get(
        StackComponentType.SECRETS_MANAGER, []
    )

    configuration = {}
    flavor: Optional[str] = None
    if len(mandatory_secrets_managers) > 0:
        flavor = mandatory_secrets_managers[0].flavor
        configuration = mandatory_secrets_managers[0].configuration.copy()
    elif len(optional_secrets_managers) > 0:
        flavor = optional_secrets_managers[0].flavor
        configuration = optional_secrets_managers[0].configuration.copy()
    else:
        raise RuntimeError(
            "No secrets manager found in the current environment."
        )

    logging.debug(
        f"Creating secrets manager of flavor '{flavor}' and config:"
        f" {configuration}"
    )

    configuration["namespace"] = None
    name = kwargs.pop("name", f"zenml_pytest_{random_str(16).lower()}")
    configuration.update(**kwargs)

    secrets_manager_model = Client().create_stack_component(
        name=name,
        component_type=StackComponentType.SECRETS_MANAGER,
        flavor=flavor,
        configuration=configuration,
    )

    yield cast(
        BaseSecretsManager,
        StackComponent.from_model(secrets_manager_model),
    )

    if not no_cleanup:
        Client().deregister_stack_component(
            name_id_or_prefix=secrets_manager_model.id,
            component_type=StackComponentType.SECRETS_MANAGER,
        )


def get_arbitrary_secret(name: Optional[str] = None) -> ArbitrarySecretSchema:
    name = name or f"pytest{random_str(16).lower()}"
    key = f"key_{random_str(16)}"
    value = f"{random_str(64)}"
    secret = ArbitrarySecretSchema(name=name)
    secret.arbitrary_kv_pairs[key] = value
    return secret
