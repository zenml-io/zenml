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

import datetime
import os
from typing import Optional, Tuple

import requests
from slack_sdk import WebClient


def get_channel_id_from_name(name: str) -> str:
    """Gets a channel ID from a Slack channel name.

    Args:
        name: Name of the channel.

    Returns:
        Channel ID.
    """
    client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
    response = client.conversations_list()
    conversations = response["channels"]
    if id := [c["id"] for c in conversations if c["name"] == name][0]:
        return id
    else:
        raise ValueError(f"Channel {name} not found.")


SLACK_CHANNEL_IDS = [get_channel_id_from_name("general")]


def page_exists(url: str) -> bool:
    import requests

    r = requests.get(url, timeout=5)
    return r.status_code == 200


def get_release_date(
    package_name: str, version: str
) -> Tuple[datetime.datetime, Optional[datetime.datetime]]:
    """Get the release date of a package version.

    Args:
        package_name: Name of the package.
        version: Version of the package.

    Returns:
        The release date of the package version, and the date of the next
        release if it exists (or None).
    """
    # Get the package's release information from the PyPI API
    response = requests.get(
        f"https://pypi.org/pypi/{package_name}/json", timeout=5
    )

    # Parse the JSON data
    data = response.json()

    # Get a list of the package's release versions
    release_info = data["releases"].get(version)

    if not release_info:
        raise ValueError(
            f"Version {version} not found for package {package_name}."
        )
    release_upload_time = datetime.datetime.strptime(
        data["releases"][version][0]["upload_time"], "%Y-%m-%dT%H:%M:%S"
    )

    two_weeks_later = release_upload_time + datetime.timedelta(weeks=2)
    if two_weeks_later > datetime.datetime.now():
        two_weeks_later = datetime.datetime.now()

    return (
        release_upload_time,
        two_weeks_later,
    )
