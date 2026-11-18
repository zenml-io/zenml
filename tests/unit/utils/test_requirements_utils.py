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
from importlib.metadata import version

import pytest

from zenml.cli.utils import install_packages
from zenml.utils import requirements_utils


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="The expression is POSIX shell syntax that only runs in Linux images.",
)
def test_installed_zenml_shell_requirement():
    """Tests that the shell expression pins the installed ZenML version."""
    expression = requirements_utils.INSTALLED_ZENML_SHELL_REQUIREMENT.replace(
        "pip", f'"{sys.executable}" -m pip', 1
    )

    output = subprocess.run(
        f"echo {expression}",
        shell=True,  # nosec B602
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    assert output.strip() == f"zenml=={version('zenml')}"


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


def test_install_packages_pins_installed_zenml(mocker):
    """Tests that CLI installs include the installed ZenML version."""
    check_call = mocker.patch("zenml.cli.utils.subprocess.check_call")

    install_packages(["sagemaker"])

    assert f"zenml=={version('zenml')}" in check_call.call_args.args[0]
