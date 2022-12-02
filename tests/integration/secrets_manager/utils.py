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
import os
from typing import Any, Optional, cast

import pytest

from zenml.client import Client
from zenml.enums import StackComponentType
from zenml.secret.arbitrary_secret_schema import ArbitrarySecretSchema
from zenml.secrets_managers.base_secrets_manager import BaseSecretsManager
from zenml.stack import StackComponent
from zenml.utils.string_utils import random_str


def get_secrets_manager(
    request: pytest.FixtureRequest,
    **kwargs: Any,
) -> BaseSecretsManager:
    """Utility function to create secrets managers of different flavors.

    This function is used to instantiate Secrets Managers of different flavors
    to use in integration testing:

    For AWS:

    * set up local AWS client and credentials.
    * run with `pytest tests/integration/secrets_manager --secrets-manager-flavor aws`.
    * the Secrets Manager will use the `eu-west-2` region, which is dedicated to
    integration testing.

    For GCP:

    * create a GCP service account and a key with full access to the
    `zenml-secrets-manager` project. Set the `GOOGLE_APPLICATION_CREDENTIALS`
    environment variable to point to the downloaded key JSON file.
    * run with `pytest tests/integration/secrets_manager --secrets-manager-flavor gcp`.

    For Azure:

    * set up local Azure client and credentials.
    * run with `pytest tests/integration/secrets_manager --secrets-manager-flavor azure`.

    For HashiCorp Vault:

    * install vault on your system.
    * start a vault development instance with `vault server --dev` and note
    the cluster's address and token
    * set the VAULT_ADDR and VAULT_TOKEN environment variables to the cluster
    address and token
    * run with `pytest tests/integration/secrets_manager --secrets-manager-flavor vault`.
    """
    client = Client()
    flavor = request.config.getoption("secrets_manager_flavor")

    name = kwargs.pop("name", f"zenml_pytest_{random_str(16).lower()}")
    configuration = kwargs.copy()

    if flavor == "local":
        # nothing to do here
        pass
    elif flavor == "aws":
        configuration.update(
            dict(
                region_name="eu-west-2",
            )
        )
    elif flavor == "gcp":
        configuration.update(
            dict(
                project_id="zenml-secrets-manager",
            )
        )
    elif flavor == "azure":
        configuration.update(
            dict(
                key_vault_name="zenml-pytest",
            )
        )
    elif flavor == "vault":
        url = os.getenv("VAULT_ADDR")
        token = os.getenv("VAULT_TOKEN")
        if url and token:
            configuration.update(
                dict(
                    url=url,
                    token=token,
                    mount_point="secret/",
                )
            )
        else:
            raise RuntimeError(
                "Tests can not be run for the vault secrets"
                "manager as the required environment variables "
                "are not set. Deploy a vault dev server locally "
                "and export the address and token: \n"
                "`export VAULT_ADDR=...` \n"
                "`export VAULT_TOKEN=...`\n"
            )
    else:
        raise RuntimeError(
            f"Secrets manager flavor {flavor} not covered in unit tests"
        )
    secrets_manager_model = client.create_stack_component(
        name=name,
        component_type=StackComponentType.SECRETS_MANAGER,
        flavor=flavor,
        configuration=configuration,
    )
    return cast(
        BaseSecretsManager,
        StackComponent.from_model(secrets_manager_model),
    )


def get_arbitrary_secret(name: Optional[str] = None) -> ArbitrarySecretSchema:
    name = name or f"pytest{random_str(16).lower()}"
    key = f"key_{random_str(16)}"
    value = f"{random_str(64)}"
    secret = ArbitrarySecretSchema(name=name)
    secret.arbitrary_kv_pairs[key] = value
    return secret
