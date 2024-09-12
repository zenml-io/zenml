#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

from typing import List

from pydantic import BaseModel

from zenml.utils import string_utils


def test_get_human_readable_time_formats_correctly() -> None:
    """Check the get_human_readable_time function formats the string correctly."""
    assert string_utils.get_human_readable_time(172799) == "1d23h59m59s"
    assert string_utils.get_human_readable_time(3661) == "1h1m1s"
    assert string_utils.get_human_readable_time(3661) == "1h1m1s"
    assert string_utils.get_human_readable_time(301) == "5m1s"
    assert string_utils.get_human_readable_time(0.1234) == "0.123s"
    assert string_utils.get_human_readable_time(-300) == "-5m0s"


def test_get_human_readable_filesize_formats_correctly() -> None:
    """Check the get_human_readable_filesize function formats the string correctly."""
    assert string_utils.get_human_readable_filesize(1023) == "1023.00 B"
    assert string_utils.get_human_readable_filesize(1024) == "1.00 KiB"
    assert (
        string_utils.get_human_readable_filesize(int(1.5 * 1024 * 1024 * 1024))
        == "1.50 GiB"
    )


def test_random_str_is_random() -> None:
    """Test that random_str returns a random string."""
    lst: List[str] = []
    for _ in range(10000):
        new_str = string_utils.random_str(16)
        assert new_str not in lst
        lst.append(new_str)


def test_string_substitution() -> None:
    """Test string substitution."""

    class ModelClass(BaseModel):
        string_attribute: str
        int_attribute: int

    model = ModelClass(string_attribute="string_value", int_attribute=1)
    model_sub = ModelClass(
        string_attribute="string_value_suffix", int_attribute=1
    )
    def substitution_func(s):
        return s + "_suffix"

    assert (
        string_utils.substitute_string(1, substitution_func=substitution_func)
        == 1
    )
    assert (
        string_utils.substitute_string(
            0.1, substitution_func=substitution_func
        )
        == 0.1
    )
    assert (
        string_utils.substitute_string(
            None, substitution_func=substitution_func
        )
        is None
    )
    assert string_utils.substitute_string(
        ["a", "b", 1], substitution_func=substitution_func
    ) == ["a_suffix", "b_suffix", 1]
    assert string_utils.substitute_string(
        ("a", "b", 1), substitution_func=substitution_func
    ) == ("a_suffix", "b_suffix", 1)
    assert string_utils.substitute_string(
        set(["a", "b", 1]), substitution_func=substitution_func
    ) == set(["a_suffix", "b_suffix", 1])
    assert string_utils.substitute_string(
        {"key": "value"}, substitution_func=substitution_func
    ) == {"key_suffix": "value_suffix"}
    assert (
        string_utils.substitute_string(
            model, substitution_func=substitution_func
        )
        == model_sub
    )

    combined = [
        2,
        0.2,
        None,
        "string",
        {3: "value", "key": model},
        set(["set_value", 4]),
    ]
    assert string_utils.substitute_string(
        combined, substitution_func=substitution_func
    ) == [
        2,
        0.2,
        None,
        "string_suffix",
        {3: "value_suffix", "key_suffix": model_sub},
        set(["set_value_suffix", 4]),
    ]
