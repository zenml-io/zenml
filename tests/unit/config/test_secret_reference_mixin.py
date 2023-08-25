#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
import json
from contextlib import ExitStack as does_not_raise

import pytest
from pydantic import validator

from zenml.client import Client
from zenml.config.secret_reference_mixin import SecretReferenceMixin
from zenml.enums import StackComponentType
from zenml.secret import ArbitrarySecretSchema
from zenml.secrets_managers import LocalSecretsManagerFlavor
from zenml.utils import secret_utils


class MixinSubclass(SecretReferenceMixin):
    """Secret reference mixin subclass."""

    value: str


def test_secret_references_are_not_allowed_for_clear_text_fields():
    """Tests that secret references are not allowed for fields explicitly marked
    as clear text fields."""

    class C(SecretReferenceMixin):
        value: str = secret_utils.ClearTextField()

    with pytest.raises(ValueError):
        C(value="{{name.key}}")


def test_secret_references_are_not_allowed_for_fields_with_validators():
    """Tests that secret references are not allowed for fields requiring a
    pydantic validator."""

    class C(SecretReferenceMixin):
        value: str

        @validator("value")
        def validate(value):
            return value

    with pytest.raises(ValueError):
        C(value="{{name.key}}")


def test_secret_reference_mixin_returns_correct_required_secrets():
    """Tests that the secret reference mixing correctly detects all secret
    references."""
    assert MixinSubclass(value="plain text").required_secrets == set()

    secrets = MixinSubclass(value="{{name.key}}").required_secrets
    assert len(secrets) == 1
    secret_ref = secrets.pop()
    assert secret_ref.name == "name"
    assert secret_ref.key == "key"


def test_secret_reference_mixin_serialization_does_not_resolve_secrets():
    """Tests that the serialization of a secret reference mixing
    doesn't resolve secret references."""
    secret_ref = "{{name.key}}"

    assert MixinSubclass(value=secret_ref).dict()["value"] == secret_ref
    assert (
        json.loads(MixinSubclass(value=secret_ref).json())["value"]
        == secret_ref
    )


def test_secret_reference_resolving(clean_client: Client):
    """Tests the secret resolving of the mixin class."""
    obj = MixinSubclass(value="{{secret.key}}")

    # No active secrets manager
    with pytest.raises(RuntimeError):
        _ = obj.value

    flavor = LocalSecretsManagerFlavor()
    clean_client.create_stack_component(
        "local_secrets_manager",
        flavor=flavor.name,
        component_type=flavor.type,
        configuration={},
        component_spec_path=None,
    )
    components = {
        StackComponentType.ORCHESTRATOR: clean_client.get_stack_component(
            component_type=StackComponentType.ORCHESTRATOR
        ).id,
        StackComponentType.ARTIFACT_STORE: clean_client.get_stack_component(
            component_type=StackComponentType.ARTIFACT_STORE
        ).id,
        flavor.type: "local_secrets_manager",
    }
    clean_client.create_stack(name="stack", components=components)
    clean_client.activate_stack("stack")

    # Secret missing
    with pytest.raises(KeyError):
        _ = obj.value

    secrets_manager = clean_client.active_stack.secrets_manager
    assert secrets_manager

    secret_without_correct_key = ArbitrarySecretSchema(
        name="secret", wrong_key="value"
    )
    secrets_manager.register_secret(secret_without_correct_key)

    # Key missing in secret
    with pytest.raises(KeyError):
        _ = obj.value

    secret_with_correct_key = ArbitrarySecretSchema(name="secret", key="value")
    secrets_manager.update_secret(secret_with_correct_key)

    with does_not_raise():
        _ = obj.value
