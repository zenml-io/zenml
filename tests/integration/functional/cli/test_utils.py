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
import io
import json
from unittest.mock import patch

import pytest
import yaml
from click import ClickException

from zenml.cli import utils as cli_utils
from zenml.cli.utils import requires_mac_env_var_warning
from zenml.constants import (
    ENV_ZENML_CLI_MACHINE_MODE,
    ENV_ZENML_DEFAULT_OUTPUT,
)


def test_error_raises_exception():
    """Tests that the error method raises an exception."""
    with pytest.raises(ClickException):
        cli_utils.error("boom")


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
    "output_format,loader",
    [("json", json.loads), ("yaml", yaml.safe_load)],
)
def test_prepare_output_filters_columns_for_structured_formats(
    output_format, loader
):
    """Tests column filtering for JSON and YAML output."""
    rendered = cli_utils.prepare_output(
        data=[{"id": "1", "name": "aria", "status": "active"}],
        output_format=output_format,
        columns="name,status",
    )

    payload = loader(rendered)
    assert payload == {"items": [{"name": "aria", "status": "active"}]}


def test_get_default_output_format_prefers_machine_mode(monkeypatch):
    """Tests that machine mode overrides the default output env var."""
    monkeypatch.setenv(ENV_ZENML_DEFAULT_OUTPUT, "yaml")
    monkeypatch.setenv(ENV_ZENML_CLI_MACHINE_MODE, "true")

    assert cli_utils.is_machine_mode() is True
    assert cli_utils.get_default_output_format() == "json"


def test_confirmation_auto_yes_in_machine_mode(monkeypatch):
    """Tests that machine mode auto-confirms prompts."""
    monkeypatch.setenv(ENV_ZENML_CLI_MACHINE_MODE, "true")

    with patch("zenml.cli.utils.RichConfirm.ask") as confirm:
        assert cli_utils.confirmation("Delete?") is True

    confirm.assert_not_called()


def test_prompt_fails_in_machine_mode(monkeypatch):
    """Tests that prompt helper fails fast in machine mode."""
    monkeypatch.setenv(ENV_ZENML_CLI_MACHINE_MODE, "true")

    with pytest.raises(ClickException):
        cli_utils.prompt("Provide a value")


def test_error_outputs_structured_json_in_machine_mode(monkeypatch):
    """Tests structured machine-readable error output."""
    monkeypatch.setenv(ENV_ZENML_CLI_MACHINE_MODE, "true")

    with pytest.raises(ClickException) as exc_info:
        cli_utils.error("boom", error_type="ExampleError", exit_code=7)

    output = io.StringIO()
    exc_info.value.show(file=output)
    assert json.loads(output.getvalue()) == {
        "error": "boom",
        "type": "ExampleError",
        "exit_code": 7,
    }


def test_multi_choice_prompt_fails_in_machine_mode(monkeypatch):
    """Tests that multi-choice prompts are blocked in machine mode."""
    monkeypatch.setenv(ENV_ZENML_CLI_MACHINE_MODE, "true")

    with pytest.raises(ClickException):
        cli_utils.multi_choice_prompt(
            object_type="stack",
            choices=[["a"]],
            headers=["name"],
            prompt_text="Pick one",
        )


def test_handle_dry_run_output_uses_machine_mode_json(monkeypatch):
    """Tests the shared dry-run payload helper."""
    monkeypatch.setenv(ENV_ZENML_CLI_MACHINE_MODE, "true")

    with patch("zenml.cli.utils.handle_output_single") as handle_output_single:
        cli_utils.handle_dry_run_output(
            action="stack.register",
            summary="Stack `aria` would be registered.",
            target={"resource": "stack", "name": "aria"},
            validated_input={"name": "aria"},
            details={"would_activate": False},
            warnings=["preview warning"],
        )

    handle_output_single.assert_called_once_with(
        data={
            "dry_run": True,
            "status": "validated",
            "action": "stack.register",
            "summary": "Stack `aria` would be registered.",
            "target": {"resource": "stack", "name": "aria"},
            "validated_input": {"name": "aria"},
            "details": {"would_activate": False},
            "warnings": ["preview warning"],
        },
        output_format="json",
    )


@pytest.mark.parametrize(
    "mac_version, env_var, expected_output",
    [
        ("10.12", "", False),
        ("10.13", "", True),
        ("10.14", "", True),
        ("10.15", "", True),
        ("11.0", "", True),
        ("12.3", "", True),
        ("13.3.5", "", True),
        ("14.5", "", True),
        ("10.12", "1", False),
        ("10.13", "1", False),
        ("10.14", "1", False),
        ("10.15", "1", False),
    ],
)
def test_requires_mac_env_var_warning(mac_version, env_var, expected_output):
    with patch("sys.platform", "darwin"):
        with patch("platform.release", return_value=mac_version):
            with patch.dict(
                "os.environ",
                {"OBJC_DISABLE_INITIALIZE_FORK_SAFETY": env_var},
                clear=True,
            ):
                assert requires_mac_env_var_warning() == expected_output


@pytest.mark.parametrize("platform", ["win32", "linux"])
def test_requires_mac_env_var_warning_non_mac(platform):
    with patch("sys.platform", platform):
        assert not requires_mac_env_var_warning()
