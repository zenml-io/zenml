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

import contextlib
import logging
import sys
import time

import pytest

from zenml.utils import daemon

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@pytest.mark.skipif(
    sys.platform == "win32", reason="Windows does not support daemonization"
)
def test_daemonize_works(tmp_path):
    """Test daemonization works."""
    tmp_pid = f"{tmp_path}/daemon.pid"
    # create a file handler
    handler = logging.FileHandler(f"{tmp_path}/application.log")
    handler.setLevel(logging.DEBUG)

    # add the handlers to the logger
    logger.addHandler(handler)

    @daemon.daemonize(pid_file=tmp_pid)
    def our_function(period: int):
        logger.info(f"I'm a daemon! I will sleep for {period} seconds.")
        time.sleep(period)
        logger.info("Done sleeping, flying away.")

    with contextlib.suppress(SystemExit):
        our_function(period=5)

    for i in range(5):
        if daemon.check_if_daemon_is_running(pid_file=tmp_pid):
            break
        time.sleep(1)
    else:
        assert "Daemon process not found"

    time.sleep(5)
    # check if the log file exists
    assert (tmp_path / "application.log").exists()

    # read the log file
    with open(f"{tmp_path}/application.log", "r") as f:
        log = f.read()
        assert "I'm a daemon" in log
        assert "Done sleeping" in log
