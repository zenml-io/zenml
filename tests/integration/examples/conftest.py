#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
from typing import Generator, Tuple

import pytest

from tests.harness.environment import TestEnvironment
from tests.harness.utils import setup_test_stack_session
from zenml.client import Client
from zenml.stack.stack import Stack


@pytest.fixture(scope="function", autouse=True)
def module_auto_setup_stack(
    check_module_requirements,
    auto_environment: Tuple[TestEnvironment, Client],
    request: pytest.FixtureRequest,
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[Stack, None, None]:
    """Fixture to automatically configure a stack adapted to the requirements of
    each test module.

    Args:
        check_module_requirements: The fixture that check the requirements of
            the current test module.
        auto_environment: The fixture that automatically creates and sets up the
            active test environment.
        request: The pytest request object.

    Yields:
        An active ZenML stack with the requirements of the test module.
    """
    no_cleanup = request.config.getoption("no_cleanup", False)
    env, client = auto_environment

    with setup_test_stack_session(
        request=request,
        tmp_path_factory=tmp_path_factory,
        environment=env,
        client=client,
        clean_repo=True,
        # requirements are checked in check_module_requirements
        check_requirements=False,
        no_cleanup=no_cleanup,
    ) as stack:
        yield stack
