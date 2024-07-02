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
import os
from unittest.mock import patch

import pytest
from click import ClickException

from zenml import __version__ as current_zenml_version
from zenml.cli import utils as cli_utils
from zenml.cli.utils import requires_mac_env_var_warning


def test_error_raises_exception():
    """Tests that the error method raises an exception."""
    with pytest.raises(Exception):
        cli_utils.error()


def test_file_expansion_works(tmp_path):
    """Tests that we can get the contents of a file."""
    sample_text_value = "aria, blupus and axl are the best friends ever"
    not_from_file_value = "this is not from a file"
    file_path = tmp_path / "test.txt"
    file_path.write_text(sample_text_value)

    # test that the file contents are returned
    assert (
        cli_utils.expand_argument_value_from_file(
            name="sample_text", value=f"@{file_path}"
        )
        == sample_text_value
    )

    assert (
        cli_utils.expand_argument_value_from_file(
            name="text_not_from_file", value=not_from_file_value
        )
        == not_from_file_value
    )

    non_existent_file = tmp_path / "non_existent_file.txt"
    with pytest.raises(ValueError):
        cli_utils.expand_argument_value_from_file(
            name="non_existent_file", value=f"@{non_existent_file}"
        )


def test_parsing_name_and_arguments():
    """Test that our ability to parse CLI arguments works."""
    assert cli_utils.parse_name_and_extra_arguments(["foo"]) == ("foo", {})
    assert cli_utils.parse_name_and_extra_arguments(["foo", "--bar=1"]) == (
        "foo",
        {"bar": "1"},
    )
    assert cli_utils.parse_name_and_extra_arguments(
        ["--bar=1", "foo", "--baz=2"]
    ) == (
        "foo",
        {"bar": "1", "baz": "2"},
    )

    assert cli_utils.parse_name_and_extra_arguments(
        ["foo", "--bar=![@#$%^&*()"]
    ) == ("foo", {"bar": "![@#$%^&*()"})

    with pytest.raises(ClickException):
        cli_utils.parse_name_and_extra_arguments(["--bar=1"])


def test_converting_structured_str_to_dict():
    """Test that our ability to parse CLI arguments works."""
    assert cli_utils.convert_structured_str_to_dict(
        "{'location': 'Nevada', 'aliens':'many'}"
    ) == {"location": "Nevada", "aliens": "many"}

    with pytest.raises(ClickException):
        cli_utils.convert_structured_str_to_dict(
            '{"location: "Nevada", "aliens":"many"}'
        )


def test_parsing_unknown_component_attributes():
    """Test that our ability to parse CLI arguments works."""
    assert cli_utils.parse_unknown_component_attributes(
        ["--foo", "--bar", "--baz", "--qux"]
    ) == ["foo", "bar", "baz", "qux"]
    with pytest.raises(AssertionError):
        cli_utils.parse_unknown_component_attributes(["foo"])
    with pytest.raises(AssertionError):
        cli_utils.parse_unknown_component_attributes(["foo=bar=qux"])


def test_get_package_information_works():
    """Test that the package information is returned."""
    assert (
        cli_utils.get_package_information("zenml")["zenml"]
        == current_zenml_version
    )


def test_validate_keys():
    """Test that validation of proper identifier as key works"""
    with pytest.raises(ClickException):
        cli_utils.validate_keys("12abc")
    with pytest.raises(ClickException):
        cli_utils.validate_keys("abc d")
    with pytest.raises(ClickException):
        cli_utils.validate_keys("")
    assert cli_utils.validate_keys("abcd") is None


@pytest.mark.parametrize(
    "mac_version, env_var, expected_result",
    [
        ("14.0", "", True),
        ("14.0", "1", False),
        ("13.0", "", True),
        ("13.0", "1", False),
        ("12.0", "", True),
        ("12.0", "1", False),
        ("11.0", "", True),
        ("11.0", "1", False),
        ("10.15.1", "", True),
        ("10.15.1", "1", False),
        ("10.13.0", "", True),
        ("10.13.0", "1", False),
        ("10.12.6", "", False),
        ("10.12.6", "1", False),
        ("10.11.0", "", False),
        ("10.11.0", "1", False),
    ],
)
def test_requires_mac_env_var_warning(mac_version, env_var, expected_result):
    """Test that the requires_mac_env_var_warning function works."""
    with patch(
        "platform.mac_ver", return_value=(mac_version, ("", "", ""), "x86_64")
    ), patch.dict(
        os.environ,
        {"OBJC_DISABLE_INITIALIZE_FORK_SAFETY": env_var} if env_var else {},
        clear=True,
    ):
        assert requires_mac_env_var_warning() == expected_result


def test_requires_mac_env_var_warning_non_mac():
    """Test that the requires_mac_env_var_warning function works."""
    with patch("sys.platform", "linux"):
        assert not requires_mac_env_var_warning()
