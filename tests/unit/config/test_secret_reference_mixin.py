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
from pydantic import field_validator

from zenml.client import Client
from zenml.config.secret_reference_mixin import SecretReferenceMixin
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

        @field_validator("value")
        @classmethod
        def validate(cls, value):
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

    assert MixinSubclass(value=secret_ref).model_dump()["value"] == secret_ref
    assert (
        json.loads(MixinSubclass(value=secret_ref).model_dump_json())["value"]
        == secret_ref
    )


def test_secret_reference_resolving(clean_client: Client):
    """Tests the secret resolving of the mixin class."""
    obj = MixinSubclass(value="{{secret.key}}")

    # Secret does not exist
    with pytest.raises(KeyError):
        _ = obj.value

    clean_client.create_secret("secret", values=dict(wrong_key="value"))

    # Key missing in secret
    with pytest.raises(KeyError):
        _ = obj.value

    clean_client.update_secret(
        "secret", add_or_update_values=dict(key="value")
    )

    with does_not_raise():
        _ = obj.value
