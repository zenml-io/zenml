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
"""Utility functions for networking."""

import socket
import sys
from typing import Optional, cast

from zenml.logger import get_logger

logger = get_logger(__name__)

# default scanning port range for allocating ports
SCAN_PORT_RANGE = (8000, 65535)


def port_available(port: int, address: str = "127.0.0.1") -> bool:
    """Checks if a local port is available.

    Args:
        port: TCP port number
        address: IP address on the local machine

    Returns:
        True if the port is available, otherwise False
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sys.platform != "win32":
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            else:
                # The SO_REUSEPORT socket option is not supported on Windows.
                # This if clause exists just for mypy to not complain about
                # missing code paths.
                pass
            s.bind((address, port))
    except socket.error as e:
        logger.debug("Port %d unavailable on %s: %s", port, address, e)
        return False

    return True


def find_available_port() -> int:
    """Finds a local random unoccupied TCP port.

    Returns:
        A random unoccupied TCP port.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        _, port = s.getsockname()

    return cast(int, port)


def scan_for_available_port(
    start: int = SCAN_PORT_RANGE[0], stop: int = SCAN_PORT_RANGE[1]
) -> Optional[int]:
    """Scan the local network for an available port in the given range.

    Args:
        start: the beginning of the port range value to scan
        stop: the (inclusive) end of the port range value to scan

    Returns:
        The first available port in the given range, or None if no available
        port is found.
    """
    for port in range(start, stop + 1):
        if port_available(port):
            return port
    logger.debug(
        "No free TCP ports found in the range %d - %d",
        start,
        stop,
    )
    return None


def port_is_open(hostname: str, port: int) -> bool:
    """Check if a TCP port is open on a remote host.

    Args:
        hostname: hostname of the remote machine
        port: TCP port number

    Returns:
        True if the port is open, False otherwise
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            result = sock.connect_ex((hostname, port))
            return result == 0
    except socket.error as e:
        logger.debug(
            f"Error checking TCP port {port} on host {hostname}: {str(e)}"
        )
        return False
