#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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
"""Analytics code for ZenML"""

import os
import platform
from typing import Any, Callable, Dict, Optional

import distro

from zenml import __version__
from zenml.constants import IS_DEBUG_ENV, SEGMENT_KEY_DEV, SEGMENT_KEY_PROD
from zenml.logger import get_logger

logger = get_logger(__name__)

# EVENTS

# Pipelines

RUN_PIPELINE = "Pipeline run"

GET_PIPELINES = "Pipelines fetched"

# Repo
INITIALIZE_REPO = "ZenML initialized"

# Components
REGISTERED_METADATA_STORE = "Metadata Store registered"
REGISTERED_ARTIFACT_STORE = "Artifact Store registered"
REGISTERED_ORCHESTRATOR = "Orchestrator registered"

# Stack
REGISTERED_STACK = "Stack registered"
SET_STACK = "Stack set"
FETCHED_STACK = "Stack fetched"


def get_segment_key() -> str:
    """Get key for authorizing to Segment backend.

    Returns:
        Segment key as a string.
    """
    if IS_DEBUG_ENV:
        return SEGMENT_KEY_DEV
    else:
        return SEGMENT_KEY_PROD


def in_docker() -> bool:
    """Returns: True if running in a Docker container, else False"""
    # TODO [ENG-167]: Make this more reliable and add test.
    try:
        with open("/proc/1/cgroup", "rt") as ifh:
            info = ifh.read()
            return "docker" in info or "kubepod" in info
    except (FileNotFoundError, Exception):
        return False


def in_google_colab() -> bool:
    """Returns: True if running in a Google Colab env, else False"""
    if "COLAB_GPU" in os.environ:
        return True
    return False


def in_paperspace_gradient() -> bool:
    """Returns: True if running in a Paperspace Gradient env, else False"""
    if "PAPERSPACE_NOTEBOOK_REPO_ID" in os.environ:
        return True
    return False


def get_system_info() -> Dict[str, Any]:
    """Returns system info as a dict.

    Returns:
        A dict of system information.
    """
    system = platform.system()

    if system == "Windows":
        release, version, csd, ptype = platform.win32_ver()

        return {
            "os": "windows",
            "windows_version_release": release,
            "windows_version": version,
            "windows_version_service_pack": csd,
            "windows_version_os_type": ptype,
        }

    if system == "Darwin":
        return {"os": "mac", "mac_version": platform.mac_ver()[0]}

    if system == "Linux":
        return {
            "os": "linux",
            "linux_distro": distro.id(),
            "linux_distro_like": distro.like(),
            "linux_distro_version": distro.version(),
        }

    # We don't collect data for any other system.
    return {"os": "unknown"}


def track_event(event: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """
    Track segment event if user opted-in.

    Args:
        event: Name of event to track in segment.
        metadata: Dict of metadata to track.
    """
    try:
        import analytics

        if analytics.write_key is None:
            analytics.write_key = get_segment_key()

        assert (
            analytics.write_key is not None
        ), "Analytics key not set but trying to make telemetry call."

        from zenml.config.global_config import GlobalConfig

        gc = GlobalConfig()

        if not gc.analytics_opt_in and event != INITIALIZE_REPO:
            return

        if metadata is None:
            metadata = {}

        # add basics
        metadata.update(get_system_info())
        metadata.update(
            {
                "in_docker": in_docker(),
                "in_google_colab": in_google_colab(),
                "in_paperspace_gradient": in_paperspace_gradient(),
                "version": __version__,
            }
        )

        analytics.track(str(gc.user_id), event, metadata)
        logger.debug(
            f"Analytics sent: User: {gc.user_id}, Event: {event}, Metadata: "
            f"{metadata}"
        )
    except Exception as e:
        # We should never fail main thread
        logger.debug(f"Analytics failed due to: {e}")


def parametrized(
    dec: Callable[..., Callable[..., Any]]
) -> Callable[..., Callable[[Callable[..., Any]], Callable[..., Any]]]:
    """This is a meta-decorator, that is, a decorator for decorators.
    As a decorator is a function, it actually works as a regular decorator
    with arguments:"""

    def layer(
        *args: Any, **kwargs: Any
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Internal layer"""

        def repl(f: Callable[..., Any]) -> Callable[..., Any]:
            """Internal repl"""
            return dec(f, *args, **kwargs)

        return repl

    return layer


@parametrized
def track(
    func: Callable[..., Any], event: Optional[str] = None
) -> Callable[..., Any]:
    """Decorator to track event.

    Args:
        func: Function that is decorated.
        event: Event string to stamp with.
    """
    # Need to redefine the name for the event here in order for mypy
    # to recognize it's not an optional string anymore
    # TODO [ENG-168]: open bug ticket and link here
    event_name = event or func.__name__  # default to name of function
    metadata: Dict[str, Any] = {}

    def inner_func(*args: Any, **kwargs: Any) -> Any:
        """Inner decorator function."""
        track_event(event_name, metadata=metadata)
        result = func(*args, **kwargs)
        return result

    return inner_func
