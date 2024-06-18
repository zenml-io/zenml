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

from hypothesis import given
from hypothesis.strategies import from_regex
from pydantic import BaseModel, Field

from zenml.utils import secret_utils

strategy = from_regex(r"[^.{}\s]{1,20}", fullmatch=True)


@given(name=strategy, key=strategy)
def test_is_secret_reference(name, key):
    """Check that secret reference detection works correctly."""
    assert secret_utils.is_secret_reference(f"{{{{{name}.{key}}}}}")

    # invalid references
    for value in [
        f"{{{{{name} . {key}}}}}",  # spaces
        f"{{{name}.{key}}}",  # single {}
        f"${name}.{key}",
        f"${{{{{name}.{key}}}}}",  # leading dollar
        "{{namekeynodot}}",  # no dot
        f"${{{{{name}.{key}}}}}",  # leading dollar
    ]:
        assert not secret_utils.is_secret_reference(value)


@given(name=strategy, key=strategy)
def test_secret_reference_parsing(name, key):
    """Tests that secret reference parsing works correctly."""
    for value in [
        f"{{{{{name}.{key}}}}}",  # no spaces
        f"{{{{ {name}.{key} }}}}",  # spaces
        f"{{{{   {name}.{key}     }}}}",  # more spaces
    ]:
        ref = secret_utils.parse_secret_reference(value)
        assert ref.name == name
        assert ref.key == key


def test_secret_field():
    """Tests that the secret field inserts the correct property into the pydantic field info."""
    field_info = secret_utils.SecretField()
    assert (
        field_info.json_schema_extra[
            secret_utils.PYDANTIC_SENSITIVE_FIELD_MARKER
        ]
        is True
    )


def test_secret_field_detection():
    """Tests that secret fields get correctly detected."""

    class Model(BaseModel):
        non_secret: str = Field()
        secret: str = secret_utils.SecretField()

    assert (
        secret_utils.is_secret_field(Model.model_fields["non_secret"]) is False
    )
    assert secret_utils.is_secret_field(Model.model_fields["secret"]) is True
