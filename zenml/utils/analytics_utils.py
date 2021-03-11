#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
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

import platform
import sys
from typing import Text

import analytics
import distro
import requests

from zenml.constants import IS_DEBUG_ENV
from zenml.logger import get_logger
from zenml.version import __version__

logger = get_logger(__name__)

# EVENTS

# Datasources

GET_DATASOURCES = "Datasources listed"

CREATE_DATASOURCE = "Datasource created"

# Functions

CREATE_STEP = "Step created"

GET_STEPS_VERSIONS = "Step Versions listed"

GET_STEP_VERSION = "Step listed"

# Pipelines

CREATE_PIPELINE = "Pipeline created"

REGISTER_PIPELINE = "Pipeline registered"

RUN_PIPELINE = "Pipeline run"

GET_PIPELINES = "Pipelines fetched"

GET_PIPELINE_ARTIFACTS = "Pipeline Artifacts fetched"

# Repo

CREATE_REPO = "Repository created"

INITIALIZE = "ZenML initialized"


def get_segment_key() -> Text:
    if IS_DEBUG_ENV:
        url = 'https://zenml.io/dev.analytics.json'
    else:
        url = 'https://zenml.io/analytics.json'

    headers = {"content-type": "application/json"}

    try:
        r = requests.get(url, headers=headers, timeout=5)
        return r.json()['id']
    except requests.exceptions.RequestException:
        logger.debug("Failed to get segment write key", exc_info=True)


analytics.write_key = get_segment_key()


def get_system_info():
    system = platform.system()

    if system == "Windows":
        version = sys.getwindowsversion()

        return {
            "os": "windows",
            "windows_version_build": version.build,
            "windows_version_major": version.major,
            "windows_version_minor": version.minor,
            "windows_version_service_pack": version.service_pack,
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


def track_event(event, metadata=None):
    """
    Track segment event if user opted-in.

    Args:
        event: name of event to track in segment.
        metadata: dict of metadata
    """
    try:
        from zenml.repo import GlobalConfig
        config = GlobalConfig.get_instance()
        opt_in = config.get_analytics_opt_in()
        logger.debug(f"Analytics opt-in: {opt_in}.")

        if opt_in is False and event is not INITIALIZE:
            return

        user_id = config.get_user_id()

        if metadata is None:
            metadata = {}

        # add basics
        metadata.update(get_system_info())
        metadata.update({'version': __version__})

        analytics.track(user_id, event, metadata)
        logger.debug(
            f'Analytics sent: User: {user_id}, Event: {event}, Metadata: '
            f'{metadata}')
    except Exception as e:
        # We should never fail main thread
        logger.debug(f'Analytics failed due to: {e}')
        return


def parametrized(dec):
    """This is a meta-decorator, that is, a decorator for decorators.
    As a decorator is a function, it actually works as a regular decorator
    with arguments:"""

    def layer(*args, **kwargs):
        def repl(f):
            return dec(f, *args, **kwargs)

        return repl

    return layer


@parametrized
def track(func, event=None):
    if event is None:
        event = func.__name__  # default to name of function

    metadata = {}

    # TODO: [LOW] See if we can get anonymized data from func
    # if func.__name__:
    #     metadata['function'] = func.__name__
    # if func.__module__:
    #     metadata['module'] = func.__module__

    def inner_func(*args, **kwargs):
        track_event(event, metadata=metadata)
        result = func(*args, **kwargs)
        return result

    return inner_func
