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
"""Test zenml tag CLI commands."""

import pytest
from click.testing import CliRunner

from tests.integration.functional.cli.utils import (
    random_resource_name,
    tags_killer,
)
from zenml.cli.cli import cli
from zenml.client import Client
from zenml.enums import ColorVariants
from zenml.models import TagResponse


def test_tag_list():
    """Test that zenml tag list does not fail."""
    with tags_killer():
        runner = CliRunner(mix_stderr=False)
        list_command = cli.commands["tag"].commands["list"]
        result = runner.invoke(list_command)
        assert result.exit_code == 0, result.stderr


def test_tag_create_short_names():
    """Test that zenml tag create does not fail with short names."""
    with tags_killer(0):
        runner = CliRunner(mix_stderr=False)
        create_command = cli.commands["tag"].commands["register"]
        tag_name = random_resource_name()
        result = runner.invoke(
            create_command,
            args=["-n", tag_name, "-c", ColorVariants.PURPLE.value],
        )
        assert result.exit_code == 0, result.stderr

        tag = Client().get_tag(tag_name)
        assert tag.name == tag_name
        assert tag.color == ColorVariants.PURPLE


def test_tag_create_full_names():
    """Test that zenml tag create does not fail with full names."""
    with tags_killer(0):
        runner = CliRunner(mix_stderr=False)
        create_command = cli.commands["tag"].commands["register"]
        tag_name = random_resource_name()
        result = runner.invoke(
            create_command,
            args=["--name", tag_name, "--color", ColorVariants.PURPLE.value],
        )
        assert result.exit_code == 0, result.stderr

        tag = Client().get_tag(tag_name)
        assert tag.name == tag_name
        assert tag.color == ColorVariants.PURPLE


def test_tag_create_only_required():
    """Test that zenml tag create does not fail."""
    with tags_killer(0):
        runner = CliRunner(mix_stderr=False)
        create_command = cli.commands["tag"].commands["register"]
        tag_name = random_resource_name()
        result = runner.invoke(
            create_command,
            args=[
                "--name",
                tag_name,
            ],
        )
        assert result.exit_code == 0, result.stderr

        tag = Client().get_tag(tag_name)
        assert tag.name == tag_name
        assert len(tag.color)


def test_tag_update():
    """Test that zenml tag update does not fail."""
    with tags_killer(1) as tags:
        tag: TagResponse = tags[0]
        runner = CliRunner(mix_stderr=False)
        update_command = cli.commands["tag"].commands["update"]
        color_to_set = "yellow" if tag.color.value != "yellow" else "grey"
        result = runner.invoke(
            update_command,
            args=[
                str(tag.id),
                "-c",
                color_to_set,
                "-n",
                "new_name",
            ],
        )
        assert result.exit_code == 0, result.stderr

        updated_tag = Client().get_tag(tag.id)
        assert tag.name != updated_tag.name
        assert tag.color != updated_tag.color
        assert updated_tag.name == "new_name"
        assert updated_tag.color.value == color_to_set

        result = runner.invoke(
            update_command,
            args=["new_name", "-c", "purple"],
        )
        assert result.exit_code == 0, result.stderr

        updated_tag = Client().get_tag(tag.id)
        assert updated_tag.name == "new_name"
        assert updated_tag.color.value == "purple"

        result = runner.invoke(
            update_command,
            args=[str(tag.id), "-n", "new_name2"],
        )
        assert result.exit_code == 0, result.stderr

        updated_tag = Client().get_tag(tag.id)
        assert updated_tag.name == "new_name2"
        assert updated_tag.color.value == "purple"


def test_tag_create_without_required_fails():
    """Test that zenml tag create fails."""
    with tags_killer(0):
        runner = CliRunner(mix_stderr=False)
        create_command = cli.commands["tag"].commands["register"]
        result = runner.invoke(
            create_command,
        )
        assert result.exit_code != 0, result.stderr


def test_tag_delete_found():
    """Test that zenml tag delete does not fail."""
    with tags_killer(1) as tags:
        tag: TagResponse = tags[0]
        runner = CliRunner(mix_stderr=False)
        delete_command = cli.commands["tag"].commands["delete"]
        result = runner.invoke(
            delete_command,
            args=[tag.name, "-y"],
        )
        assert result.exit_code == 0, result.stderr

        with pytest.raises(KeyError):
            Client().get_tag(tag.name)


def test_tag_delete_not_found():
    """Test that zenml tag delete fail."""
    with tags_killer(0):
        runner = CliRunner(mix_stderr=False)
        delete_command = cli.commands["tag"].commands["delete"]
        result = runner.invoke(
            delete_command,
            args=["some_name", "-y"],
        )
        assert result.exit_code != 0, result.stderr
