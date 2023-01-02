#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

import sys
import tempfile

import pytest

from zenml.utils import daemon

DAEMON_PID_FILE = f"{tempfile.gettempdir()}/daemon.pid"


@pytest.fixture
def daemonize_fixture():
    """Fixture to test daemonization."""

    # @daemon.daemonize(pid_file=DAEMON_PID_FILE)
    # def aria_daemon():
    #     print("I am Aria's daemon.")

    # aria_daemon()
    # time.sleep(1)  # wait for daemon to start up
    yield
    daemon.stop_daemon(DAEMON_PID_FILE)


@pytest.mark.skipif(
    sys.platform == "win32", reason="Windows does not support daemonization"
)
def test_daemonize_works(daemonize_fixture):
    """Test daemonization works."""

    assert not daemon.check_if_daemon_is_running(DAEMON_PID_FILE)
