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
"""Test zenml Model Control Plane CLI commands."""

from uuid import uuid4

import pytest
from click.testing import CliRunner

from tests.integration.functional.cli.conftest import NAME, PREFIX
from zenml.cli.cli import cli
from zenml.client import Client


def test_model_list(clean_client_with_models: "Client"):
    """Test that zenml model list does not fail."""
    runner = CliRunner(mix_stderr=False)
    list_command = cli.commands["model"].commands["list"]
    result = runner.invoke(list_command)
    assert result.exit_code == 0, result.stderr


def test_model_create_short_names(clean_client_with_models: "Client"):
    """Test that zenml model create does not fail with short names."""
    runner = CliRunner(mix_stderr=False)
    create_command = cli.commands["model"].commands["register"]
    model_name = PREFIX + str(uuid4())
    result = runner.invoke(
        create_command,
        args=[
            "-n",
            model_name,
            "-l",
            "a",
            "-d",
            "b",
            "-a",
            "c",
            "-u",
            "d",
            "--tradeoffs",
            "f",
            "-e",
            "g",
            "--limitations",
            "e",
            "-t",
            "i",
            "-t",
            "j",
            "-t",
            "k",
            "-s",
            "true",
        ],
    )
    assert result.exit_code == 0, result.stderr

    model = clean_client_with_models.get_model(model_name)
    assert model.name == model_name
    assert model.license == "a"
    assert model.description == "b"
    assert model.audience == "c"
    assert model.use_cases == "d"
    assert model.trade_offs == "f"
    assert model.ethics == "g"
    assert model.limitations == "e"
    assert model.save_models_to_registry
    assert {t.name for t in model.tags} == {"i", "j", "k"}


def test_model_create_full_names(clean_client_with_models: "Client"):
    """Test that zenml model create does not fail with full names."""
    runner = CliRunner(mix_stderr=False)
    create_command = cli.commands["model"].commands["register"]
    model_name = PREFIX + str(uuid4())
    result = runner.invoke(
        create_command,
        args=[
            "--name",
            model_name,
            "--license",
            "a",
            "--description",
            "b",
            "--audience",
            "c",
            "--use-cases",
            "d",
            "--tradeoffs",
            "f",
            "--ethical",
            "g",
            "--limitations",
            "e",
            "--tag",
            "i",
            "--tag",
            "j",
            "--tag",
            "k",
            "--save-models-to-registry",
            "false",
        ],
    )
    assert result.exit_code == 0, result.stderr

    model = clean_client_with_models.get_model(model_name)
    assert model.name == model_name
    assert model.license == "a"
    assert model.description == "b"
    assert model.audience == "c"
    assert model.use_cases == "d"
    assert model.trade_offs == "f"
    assert model.ethics == "g"
    assert model.limitations == "e"
    assert not model.save_models_to_registry
    assert {t.name for t in model.tags} == {"i", "j", "k"}


def test_model_create_only_required(clean_client_with_models: "Client"):
    """Test that zenml model create does not fail."""
    runner = CliRunner(mix_stderr=False)
    create_command = cli.commands["model"].commands["register"]
    model_name = PREFIX + str(uuid4())
    result = runner.invoke(
        create_command,
        args=["--name", model_name],
    )
    assert result.exit_code == 0, result.stderr

    model = clean_client_with_models.get_model(model_name)
    assert model.name == model_name
    assert model.license is None
    assert model.description is None
    assert model.audience is None
    assert model.use_cases is None
    assert model.trade_offs is None
    assert model.ethics is None
    assert model.limitations is None
    assert model.save_models_to_registry
    assert len(model.tags) == 0


def test_model_update(clean_client_with_models: "Client"):
    """Test that zenml model update does not fail."""
    runner = CliRunner(mix_stderr=False)
    update_command = cli.commands["model"].commands["update"]
    result = runner.invoke(
        update_command,
        args=[NAME, "--tradeoffs", "foo", "-t", "a"],
    )
    assert result.exit_code == 0, result.stderr

    model = clean_client_with_models.get_model(NAME)
    assert model.trade_offs == "foo"
    assert {t.name for t in model.tags} == {"a"}
    assert model.description is None

    result = runner.invoke(
        update_command,
        args=[NAME, "-d", "bar", "-r", "a", "-t", "b", "-s", "false"],
    )
    assert result.exit_code == 0, result.stderr

    model = clean_client_with_models.get_model(NAME)
    assert model.trade_offs == "foo"
    assert {t.name for t in model.tags} == {"b"}
    assert model.description == "bar"
    assert not model.save_models_to_registry


def test_model_create_without_required_fails(
    clean_client_with_models: "Client",
):
    """Test that zenml model create fails."""
    runner = CliRunner(mix_stderr=False)
    create_command = cli.commands["model"].commands["register"]
    result = runner.invoke(
        create_command,
    )
    assert result.exit_code != 0, result.stderr


def test_model_delete_found(clean_client_with_models: "Client"):
    """Test that zenml model delete does not fail."""
    runner = CliRunner(mix_stderr=False)
    name = PREFIX + str(uuid4())
    create_command = cli.commands["model"].commands["register"]
    runner.invoke(
        create_command,
        args=["--name", name],
    )
    delete_command = cli.commands["model"].commands["delete"]
    result = runner.invoke(
        delete_command,
        args=[name, "-y"],
    )
    assert result.exit_code == 0, result.stderr


def test_model_delete_not_found(clean_client_with_models: "Client"):
    """Test that zenml model delete fail."""
    runner = CliRunner(mix_stderr=False)
    name = PREFIX + str(uuid4())
    delete_command = cli.commands["model"].commands["delete"]
    result = runner.invoke(
        delete_command,
        args=[name],
    )
    assert result.exit_code != 0, result.stderr


def test_model_version_list(clean_client_with_models: "Client"):
    """Test that zenml model version list does not fail."""
    runner = CliRunner(mix_stderr=False)
    list_command = cli.commands["model"].commands["version"].commands["list"]
    result = runner.invoke(
        list_command,
        args=[NAME],
    )
    assert result.exit_code == 0, result.stderr


def test_model_version_list_fails_on_bad_model(
    clean_client_with_models: "Client",
):
    """Test that zenml model version list fails."""
    runner = CliRunner(mix_stderr=False)
    list_command = cli.commands["model"].commands["version"].commands["list"]
    result = runner.invoke(
        list_command,
        args=["foo"],
    )
    assert result.exit_code != 0, result.stderr


def test_model_version_delete_found(clean_client_with_models: "Client"):
    """Test that zenml model version delete does not fail."""
    runner = CliRunner(mix_stderr=False)
    model_name = PREFIX + str(uuid4())
    model_version_name = PREFIX + str(uuid4())
    model = clean_client_with_models.create_model(
        name=model_name,
    )
    clean_client_with_models.create_model_version(
        name=model_version_name,
        model_name_or_id=model.id,
    )
    delete_command = (
        cli.commands["model"].commands["version"].commands["delete"]
    )
    result = runner.invoke(
        delete_command,
        args=[model_name, model_version_name, "-y"],
    )
    assert result.exit_code == 0, result.stderr


def test_model_version_delete_not_found(clean_client_with_models: "Client"):
    """Test that zenml model version delete fail."""
    runner = CliRunner(mix_stderr=False)
    model_name = PREFIX + str(uuid4())
    model_version_name = PREFIX + str(uuid4())
    clean_client_with_models.create_model(
        name=model_name,
    )
    delete_command = (
        cli.commands["model"].commands["version"].commands["delete"]
    )
    result = runner.invoke(
        delete_command,
        args=[model_name, model_version_name, "-y"],
    )
    assert result.exit_code != 0, result.stderr


@pytest.mark.parametrize(
    "command",
    ("data_artifacts", "deployment_artifacts", "model_artifacts", "runs"),
)
def test_model_version_links_list(
    command: str, clean_client_with_models: "Client"
):
    """Test that zenml model version artifacts list fails."""
    runner = CliRunner(mix_stderr=False)
    list_command = cli.commands["model"].commands[command]
    result = runner.invoke(
        list_command,
        args=[NAME],
    )
    assert result.exit_code == 0, result.stderr


def test_model_version_update(clean_client_with_models: "Client"):
    """Test that zenml model version stage update pass."""
    runner = CliRunner(mix_stderr=False)
    update_command = (
        cli.commands["model"].commands["version"].commands["update"]
    )
    result = runner.invoke(
        update_command,
        args=[NAME, "1", "-s", "production"],
    )
    assert result.exit_code == 0, result.stderr
