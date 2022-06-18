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
from zenml.integrations.vault.secrets_manager.vault_secrets_manager import (
    get_secret_schema_name,
    prepend_secret_schema_to_secret_name,
    remove_secret_schema_name,
    sanitize_secret_name,
)
from zenml.secret.arbitrary_secret_schema import ArbitrarySecretSchema


def test_sanitize_secret_name() -> None:
    """
    Tests that the secret name is sanitized correctly.
    """
    assert sanitize_secret_name("my-secret-name") == "my_secret_name"
    assert sanitize_secret_name("my-secret_name") == "my_secret_name"


def test_prepend_secret_schema_to_secret_name() -> None:
    """
    Tests that the secret name is prepended with the secret schema name.
    """
    name = "test_name"
    some_secret_name = name
    some_arbitrary_schema = ArbitrarySecretSchema(name=some_secret_name)

    assert (
        prepend_secret_schema_to_secret_name(some_arbitrary_schema)
        == "arbitrary-test_name"
    )


def test_remove_secret_schema_name() -> None:
    """
    Tests that the secret name is removed from the secret schema name.
    """
    combined_secret_name = "arbitrary-test_name"

    assert remove_secret_schema_name(combined_secret_name) == "test_name"


def test_get_secret_schema_name() -> None:
    """
    Tests that the secret schema name is retrieved correctly.
    """
    combined_secret_name = "arbitrary-test_name"

    assert get_secret_schema_name(combined_secret_name) == "arbitrary"
