#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""The 'analytics' module of ZenML.

This module is based on the 'analytics-python' package created by Segment.
The base functionalities are adapted to work with the ZenML analytics server.
"""
from zenml.analytics.client import Client

on_error = Client.DefaultConfig.on_error
debug = Client.DefaultConfig.debug
send = Client.DefaultConfig.send
sync_mode = Client.DefaultConfig.sync_mode
max_queue_size = Client.DefaultConfig.max_queue_size
timeout = Client.DefaultConfig.timeout
max_retries = Client.DefaultConfig.max_retries


def track(*args, **kwargs):
    """Send a track call."""
    _proxy("track", *args, **kwargs)


def identify(*args, **kwargs):
    """Send a identify call."""
    _proxy("identify", *args, **kwargs)


def group(*args, **kwargs):
    """Send a group call."""
    _proxy("group", *args, **kwargs)


def _proxy(method, *args, **kwargs):
    """Create an analytics client if one doesn't exist and send to it."""
    global default_client
    if not default_client:
        default_client = Client(
            debug=debug,
            max_queue_size=max_queue_size,
            send=send,
            on_error=on_error,
            max_retries=max_retries,
            sync_mode=sync_mode,
            timeout=timeout,
        )

    fn = getattr(default_client, method)
    fn(*args, **kwargs)
