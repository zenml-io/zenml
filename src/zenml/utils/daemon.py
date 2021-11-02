import atexit
import os
import signal
import sys
import types
from typing import Any, Callable, Optional

import psutil

from zenml.logger import get_logger

logger = get_logger(__name__)


def run_as_daemon(
    daemon_function: Callable[..., Any],
    pid_file: str,
    log_file: Optional[str] = None,
) -> None:
    """Runs a function as a daemon process.

    Args:
        daemon_function: The function to run as a daemon.
        pid_file: Path to file in which to store the PID of the daemon process.
        log_file: Optional file to which the daemons stdout/stderr will be
            redirected to.
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
    os.chdir("/")
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

    # redirect standard file descriptors to devnull
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
    def sigterm(signum: signal.Signals, frame: types.FrameType) -> None:
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
