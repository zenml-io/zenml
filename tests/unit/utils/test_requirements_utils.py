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

import pytest

from zenml.cli.utils import install_packages
from zenml.utils import requirements_utils


def test_opentelemetry_constraints_dockerfile_line():
    """Tests that the Dockerfile line writes the installed SDK constraints."""
    line = requirements_utils.get_opentelemetry_constraints_dockerfile_line()
    command, output_file = line.removeprefix("RUN ").rsplit(" > ", 1)
    assert (
        output_file == requirements_utils.OPENTELEMETRY_CONSTRAINTS_FILE_NAME
    )

    output = subprocess.run(
        command.replace("python", f'"{sys.executable}"', 1),
        shell=True,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert (
        output.splitlines()
        == requirements_utils.get_opentelemetry_constraints()
    )


@pytest.mark.parametrize(
    "requirements, expected",
    [
        (["zenml[server]==0.98.1"], True),
        (["zenml-foo", "# zenml", "--index-url https://x.io"], False),
    ],
)
def test_requires_zenml(requirements, expected):
    """Tests detecting ZenML in a list of requirements."""
    assert requirements_utils.requires_zenml(requirements) is expected


def test_install_packages_adds_opentelemetry_constraints(mocker):
    """Tests that CLI installs pass the OpenTelemetry constraints."""
    mocker.patch.object(
        requirements_utils,
        "get_opentelemetry_constraints",
        return_value=["opentelemetry-api==1.43.0"],
    )
    check_call = mocker.patch("zenml.cli.utils.subprocess.check_call")

    install_packages(["sagemaker"])
    assert "-c" in check_call.call_args.args[0]

    install_packages(["zenml==0.98.1"])
    assert "-c" not in check_call.call_args.args[0]
