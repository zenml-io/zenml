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
import random

from hypothesis import given
from hypothesis.strategies import from_regex

from zenml.utils import secret_utils

strategy = from_regex(r"[^.\s]{1,100}", fullmatch=True)


@given(name=strategy, key=strategy)
def test_is_secret_reference(name, key):
    """Check that secret reference detection works correctly."""

    # valid references
    for value in [
        f"${{ {name}.{key} }}",
        f"${{{name}.{key} }}",
        f"${{ {name}.{key}}}",
        f"${{{name}.{key}}}",
    ]:
        assert secret_utils.is_secret_reference(value)

    # invalid references
    for value in [
        f"{{ {name}.{key} }}",
        f"${name}.{key}",
        f"{name}.{key}",
        "${ namekeynodot }",
    ]:
        assert not secret_utils.is_secret_reference(value)


@given(name=strategy, key=strategy)
def test_secret_reference_parsing(name, key):
    """Tests that secret reference parsing works correctly."""
    space = " " if random.random() > 0.5 else ""
    value = f"${{{space}{name}.{key}{space}}}"
    ref = secret_utils.parse_secret_reference(value)
    assert ref.name == name
    assert ref.key == key
