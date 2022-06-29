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
from typing import Dict

import pytest
from pydantic import BaseModel

from zenml.integrations.vault.secrets_manager.vault_secrets_manager import (
    get_secret_schema_name,
    prepend_secret_schema_to_secret_name,
    remove_secret_schema_name,
    sanitize_secret_name,
)
from zenml.secret.arbitrary_secret_schema import ArbitrarySecretSchema


class ZenMLSecret(BaseModel):
    zenml_secret_name: str
    expected_prepend_secret_name: str
    expected_sanitized_secret_name: str
    secrets_key_value_examples: Dict[str, str] = {"the_cat_name": "Aria"}


ZENML_SECRET = [
    ZenMLSecret(
        zenml_secret_name="secret-name",
        expected_sanitized_secret_name="secret_name",
        expected_prepend_secret_name="arbitrary-secret_name",
    ),
    ZenMLSecret(
        zenml_secret_name="test-vault@secret Example",
        expected_sanitized_secret_name="test_vault_secret_Example",
        expected_prepend_secret_name="arbitrary-test_vault_secret_Example",
    ),
    ZenMLSecret(
        zenml_secret_name="test-name__vault@secret",
        expected_sanitized_secret_name="test_name__vault_secret",
        expected_prepend_secret_name="arbitrary-test_name__vault_secret",
    ),
]


@pytest.mark.parametrize("parametrized_input", ZENML_SECRET)
def test_sanitize_secret_name(parametrized_input: ZenMLSecret) -> None:
    """
    Tests that the secret name is sanitized correctly.
    """
    assert (
        sanitize_secret_name(parametrized_input.zenml_secret_name)
        == parametrized_input.expected_sanitized_secret_name
    )


@pytest.mark.parametrize("parametrized_input", ZENML_SECRET)
def test_prepend_secret_schema_to_secret_name(
    parametrized_input: ZenMLSecret,
) -> None:
    """
    Tests that the secret name is prepended with the secret schema name.
    """
    some_arbitrary_schema = ArbitrarySecretSchema(
        name=parametrized_input.expected_sanitized_secret_name
    )

    assert (
        prepend_secret_schema_to_secret_name(some_arbitrary_schema)
        == parametrized_input.expected_prepend_secret_name
    )


@pytest.mark.parametrize("parametrized_input", ZENML_SECRET)
def test_remove_secret_schema_name(parametrized_input: ZenMLSecret) -> None:
    """
    Tests that the secret name is removed from the secret schema name.
    """
    assert (
        remove_secret_schema_name(
            parametrized_input.expected_prepend_secret_name
        )
        == parametrized_input.expected_sanitized_secret_name
    )


@pytest.mark.parametrize("parametrized_input", ZENML_SECRET)
def test_get_secret_schema_name(parametrized_input: ZenMLSecret) -> None:
    """
    Tests that the secret schema name is retrieved correctly.
    """
    assert (
        get_secret_schema_name(parametrized_input.expected_prepend_secret_name)
        == "arbitrary"
    )
