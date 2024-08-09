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

import platform

from zenml.constants import VALID_OPERATING_SYSTEMS
from zenml.environment import (
    Environment,
    get_environment,
    get_run_environment_dict,
)


def test_get_run_environment_dict():
    """Unit test for `get_run_environment_dict`.

    Tests that the function returns a dict of strings and that the following
    keys are present:
    - "environment"
    - "os"
    - "python_version"
    """
    environment_dict = get_run_environment_dict()
    assert isinstance(environment_dict, dict)
    assert "environment" in environment_dict
    assert environment_dict["environment"] == get_environment()
    assert "os" in environment_dict
    assert environment_dict["os"] == Environment.get_system_info()["os"]
    assert "python_version" in environment_dict
    assert environment_dict["python_version"] == Environment.python_version()


def test_environment_platform_info_correctness():
    """Checks that `Environment.get_system_info()` returns the correct
    platform."""
    system_id = platform.system()

    if system_id == "Darwin":
        system_id = "mac"
    elif system_id not in VALID_OPERATING_SYSTEMS:
        system_id = "unknown"

    assert system_id.lower() == Environment.get_system_info()["os"]


def test_environment_is_singleton():
    """Tests that environment is a singleton."""
    assert Environment() is Environment()


def test_ipython_terminal_detection_when_not_installed():
    """Tests that we detect if the Python process is running in an IPython terminal when not installed."""
    try:
        import IPython  # noqa
    except ImportError:
        assert Environment.in_notebook() is False
