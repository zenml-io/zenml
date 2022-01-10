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
"""Utility functions to start/stop daemon processes.

This is only implemented for UNIX systems and therefore doesn't work on
Windows. Based on
https://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
"""

import atexit
import os
import signal
import sys
import types
from typing import Any, Callable, Optional

import psutil

from zenml.logger import get_logger

logger = get_logger(__name__)

# TODO [ENG-235]: Investigate supporting Windows if Windows can run Kubeflow.

# flake8: noqa: C901
if sys.platform == "win32":
    logger.warning(
        "Daemon functionality is currently not supported on Windows."
    )
else:

    def run_as_daemon(
        daemon_function: Callable[..., Any],
        pid_file: str,
        log_file: Optional[str] = None,
        working_directory: str = "/",
    ) -> None:
        """Runs a function as a daemon process.

        Args:
            daemon_function: The function to run as a daemon.
            pid_file: Path to file in which to store the PID of the daemon process.
            log_file: Optional file to which the daemons stdout/stderr will be
                redirected to.
            working_directory: Working directory for the daemon process, defaults
                to the root directory.
        Raises:
            FileExistsError: If the PID file already exists.
        """
        # convert to absolute path as we will change working directory later
        pid_file = os.path.abspath(pid_file)
        if log_file:
            log_file = os.path.abspath(log_file)

        # check if PID file exists
        if os.path.exists(pid_file):
            raise FileExistsError(
                f"The PID file '{pid_file}' already exists, either the daemon "
                f"process is already running or something went wrong."
            )

        # first fork
        try:
            pid = os.fork()
            if pid > 0:
                # this is the process that called `run_as_daemon` so we
                # simply return so it can keep running
                return
        except OSError as e:
            logger.error("Unable to fork (error code: %d)", e.errno)
            sys.exit(1)

        # decouple from parent environment
        os.chdir(working_directory)
        os.setsid()
        os.umask(0)

        # second fork
        try:
            pid = os.fork()
            if pid > 0:
                # this is the parent of the future daemon process, kill it
                # so the daemon gets adopted by the init process
                sys.exit(0)
        except OSError as e:
            sys.stderr.write(f"Unable to fork (error code: {e.errno})")
            sys.exit(1)

        # redirect standard file descriptors to devnull (or the given logfile)
        devnull = "/dev/null"
        if hasattr(os, "devnull"):
            devnull = os.devnull

        devnull_fd = os.open(devnull, os.O_RDWR)
        log_fd = os.open(log_file, os.O_CREAT | os.O_RDWR) if log_file else None
        out_fd = log_fd or devnull_fd

        os.dup2(devnull_fd, sys.stdin.fileno())
        os.dup2(out_fd, sys.stdout.fileno())
        os.dup2(out_fd, sys.stderr.fileno())

        # write the PID file
        with open(pid_file, "w+") as f:
            f.write(f"{os.getpid()}\n")

        # register actions in case this process exits/gets killed
        def sigterm(signum: int, frame: Optional[types.FrameType]) -> None:
            """Removes the PID file."""
            os.remove(pid_file)

        def cleanup() -> None:
            """Removes the PID file."""
            os.remove(pid_file)

        signal.signal(signal.SIGTERM, sigterm)
        atexit.register(cleanup)

        # finally run the actual daemon code
        daemon_function()

    def stop_daemon(pid_file: str, kill_children: bool = True) -> None:
        """Stops a daemon process.

        Args:
            pid_file: Path to file containing the PID of the daemon process to kill.
            kill_children: If `True`, all child processes of the daemon process
                will be killed as well.
        """
        try:
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())
        except (IOError, FileNotFoundError):
            logger.warning("Daemon PID file '%s' does not exist.", pid_file)
            return

        if psutil.pid_exists(pid):
            process = psutil.Process(pid)
            if kill_children:
                for child in process.children(recursive=True):
                    child.kill()
            process.kill()
        else:
            logger.warning("PID from '%s' does not exist.", pid_file)

    def check_if_daemon_is_running(pid_file: str) -> bool:
        """Checks whether a daemon process indicated by the PID file is running.

        Args:
            pid_file: Path to file containing the PID of the daemon
                process to check.
        """
        try:
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())
        except (IOError, FileNotFoundError):
            return False

        return psutil.pid_exists(pid)
