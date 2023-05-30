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
from typing import Optional, cast
from urllib.parse import urlparse

from zenml.environment import Environment
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
            if hasattr(socket, "SO_REUSEPORT"):
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


def replace_localhost_with_internal_hostname(url: str) -> str:
    """Replaces the localhost with an internal Docker or K3D hostname in a given URL.

    Localhost URLs that are directly accessible on the host machine are not
    accessible from within a Docker or K3D container running on that same
    machine, but there are special hostnames featured by both Docker
    (`host.docker.internal`) and K3D (`host.k3d.internal`) that can be used to
    access host services from within the containers.

    Use this method to attempt to replace `localhost` in a URL with one of these
    special hostnames, if they are available inside a container.

    Args:
        url: The URL to update.

    Returns:
        The updated URL.
    """
    if not Environment.in_container():
        return url

    parsed_url = urlparse(url)
    if parsed_url.hostname in ("localhost", "127.0.0.1"):
        for internal_hostname in (
            "host.docker.internal",
            "host.k3d.internal",
        ):
            try:
                socket.gethostbyname(internal_hostname)
                parsed_url = parsed_url._replace(
                    netloc=parsed_url.netloc.replace(
                        parsed_url.hostname,
                        internal_hostname,
                    )
                )
                logger.debug(
                    f"Replacing localhost with {internal_hostname} in URL: "
                    f"{url}"
                )
                return parsed_url.geturl()

            except socket.gaierror:
                continue

    return url


def replace_internal_hostname_with_localhost(hostname: str) -> str:
    """Replaces an internal Docker or K3D hostname with localhost.

    Localhost URLs that are directly accessible on the host machine are not
    accessible from within a Docker or K3D container running on that same
    machine, but there are special hostnames featured by both Docker
    (`host.docker.internal`) and K3D (`host.k3d.internal`) that can be used to
    access host services from within the containers.

    Use this method to replace one of these special hostnames with localhost
    if used outside a container or in a container where special hostnames are
    not available.

    Args:
        hostname: The hostname to replace.

    Returns:
        The original or replaced hostname.
    """
    if hostname not in ("host.docker.internal", "host.k3d.internal"):
        return hostname

    if Environment.in_container():
        # Try to resolve one of the special hostnames to see if it is available
        # inside the container and use that if it is.
        for internal_hostname in (
            "host.docker.internal",
            "host.k3d.internal",
        ):
            try:
                socket.gethostbyname(internal_hostname)
                if internal_hostname != hostname:
                    logger.debug(
                        f"Replacing internal hostname {hostname} with "
                        f"{internal_hostname}"
                    )
                return internal_hostname
            except socket.gaierror:
                continue

    logger.debug(f"Replacing internal hostname {hostname} with localhost.")

    return "127.0.0.1"


def get_or_create_ngrok_tunnel(ngrok_token: str, port: int) -> str:
    """Get or create an ngrok tunnel at the given port.

    Args:
        ngrok_token: The ngrok auth token.
        port: The port to tunnel.

    Returns:
        The public URL of the ngrok tunnel.

    Raises:
        ImportError: If the `pyngrok` package is not installed.
    """
    try:
        from pyngrok import ngrok as ngrok_client
    except ImportError:
        raise ImportError(
            "The `pyngrok` package is required to create ngrok tunnels. "
            "Please install it by running `pip install pyngrok`."
        )

    # Check if ngrok is already tunneling the port
    tunnels = ngrok_client.get_tunnels()
    for tunnel in tunnels:
        if tunnel.config and isinstance(tunnel.config, dict):
            tunnel_protocol = tunnel.config.get("proto")
            tunnel_port = tunnel.config.get("addr")
            if tunnel_protocol == "http" and tunnel_port == port:
                return str(tunnel.public_url)

    # Create new tunnel
    ngrok_client.set_auth_token(ngrok_token)
    return str(ngrok_client.connect(port).public_url)
