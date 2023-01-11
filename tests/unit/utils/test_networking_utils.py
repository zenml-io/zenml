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

import socket

import hypothesis.strategies as st
from hypothesis import given

from zenml.utils import networking_utils


def find_open_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port


def test_port_available_works():
    """Test if port_available works."""
    open_port = find_open_port()
    assert networking_utils.port_available(open_port) is True


def test_find_available_port_works():
    """Test if find_available_port works."""
    available_port = networking_utils.find_available_port()
    assert isinstance(available_port, int)
    assert available_port <= networking_utils.SCAN_PORT_RANGE[1]
    assert available_port >= networking_utils.SCAN_PORT_RANGE[0]


def test_scan_for_available_port_works():
    """Test if scan_for_available_port works."""
    available_port = networking_utils.scan_for_available_port()
    assert isinstance(available_port, int)
    assert available_port <= networking_utils.SCAN_PORT_RANGE[1]
    assert available_port >= networking_utils.SCAN_PORT_RANGE[0]

    # the negative case, for when the port is occupied
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 65535))
        available_port = networking_utils.scan_for_available_port(65535, 65535)
        assert available_port is None


def test_port_is_open_on_local_host_works():
    """Test if port_is_open_on_local_host works."""
    open_port = find_open_port()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", open_port))
        assert networking_utils.port_is_open("127.0.0.1", open_port) is False


def test_replace_localhost_returns_url_when_running_outside_container():
    """Test method returns url when running outside container."""
    response = networking_utils.replace_localhost_with_internal_hostname(
        "http://localhost:8080"
    )
    assert response == "http://localhost:8080"
    assert isinstance(response, str)


@given(st.text())
def test_replace_internal_hostname_works(
    sample_text,
):
    """Test method returns url when not internal hostname."""
    response1 = networking_utils.replace_internal_hostname_with_localhost(
        sample_text
    )
    assert response1 == sample_text
    assert isinstance(response1, str)

    response2 = networking_utils.replace_internal_hostname_with_localhost(
        "host.docker.internal"
    )
    assert response2 == "127.0.0.1"
    assert isinstance(response2, str)
