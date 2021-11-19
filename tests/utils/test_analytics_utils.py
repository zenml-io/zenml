#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import platform
from contextlib import ExitStack as does_not_raise

from zenml.constants import VALID_OPERATING_SYSTEMS
from zenml.utils.analytics_utils import get_segment_key, get_system_info


def test_get_segment_key():
    """Checks the get_segment_key method returns a value"""
    with does_not_raise():
        get_segment_key()


def test_get_system_info_type():
    """Checks that the return value is a dictionary"""
    assert isinstance(get_system_info(), dict)


def test_platform_info_correctness():
    """Checks that the method returns the correct platform"""
    system_id = platform.system()

    if system_id == "Darwin":
        system_id = "mac"
    elif system_id not in VALID_OPERATING_SYSTEMS:
        system_id = "unknown"

    system_info = get_system_info()
    assert system_id.lower() == system_info["os"]
