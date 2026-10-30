#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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

import subprocess
import sys
from importlib.metadata import PackageNotFoundError

import pytest
from packaging.requirements import Requirement

from zenml.cli.utils import install_packages
from zenml.utils import requirements_utils


def test_get_zenml_requirements_without_zenml_distribution(mocker):
    """Tests that no requirements are returned if ZenML isn't installed."""
    mocker.patch.object(
        requirements_utils,
        "get_dependencies",
        side_effect=PackageNotFoundError("zenml"),
    )

    assert requirements_utils.get_zenml_requirements() == []


def test_zenml_requirements_dockerfile_line_skips_extras():
    """Tests that the Dockerfile line writes ZenML's non-extra requirements."""
    line = requirements_utils.get_zenml_requirements_dockerfile_line()
    command, output_file = line.removeprefix("RUN ").rsplit(" > ", 1)
    assert output_file == requirements_utils.ZENML_REQUIREMENTS_FILE_NAME

    output = subprocess.run(
        command.replace("python", f'"{sys.executable}"', 1),
        shell=True,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    names = {Requirement(r).name for r in output.splitlines()}

    expected = {
        r.name
        for r in map(Requirement, requirements_utils.get_zenml_requirements())
    }
    assert expected <= names
    # `fastapi` is only required by the `server` extra.
    assert "fastapi" not in names


@pytest.mark.parametrize(
    "requirements, expected",
    [
        (["zenml"], True),
        (["zenml==0.98.1"], True),
        (["zenml[server]>=0.98"], True),
        (["ZenML ; python_version > '3.9'"], True),
        (["zenml @ git+https://github.com/zenml-io/zenml.git"], True),
        (["zenml-foo", "zenml_bar==1.0"], False),
        (["# zenml", "--index-url https://example.com", "boto3"], False),
        ([], False),
    ],
)
def test_requires_zenml(requirements, expected):
    """Tests detecting ZenML in a list of requirements."""
    assert requirements_utils.requires_zenml(requirements) is expected


def test_install_packages_adds_zenml_requirements(mocker):
    """Tests that CLI installs include the requirements of ZenML."""
    mocker.patch.object(
        requirements_utils,
        "get_zenml_requirements",
        return_value=["opentelemetry-sdk==1.43.0"],
    )
    check_call = mocker.patch("zenml.cli.utils.subprocess.check_call")

    install_packages(["sagemaker"])
    assert "opentelemetry-sdk==1.43.0" in check_call.call_args.args[0]

    install_packages(["zenml==0.98.1"])
    assert "opentelemetry-sdk==1.43.0" not in check_call.call_args.args[0]
