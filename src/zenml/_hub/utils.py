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
"""Utility functions for the ZenML Hub."""

from typing import Optional, Tuple

from zenml._hub.constants import ZENML_HUB_ADMIN_USERNAME


def parse_plugin_name(
    plugin_name: str, author_separator: str = "/", version_separator: str = ":"
) -> Tuple[Optional[str], str, str]:
    """Helper function to parse a plugin name.

    Args:
        plugin_name: The user-provided plugin name.
        author_separator: The separator between the author username and the
            plugin name.
        version_separator: The separator between the plugin name and the
            plugin version.

    Returns:
        - The author username or None if no author was specified.
        - The plugin name.
        - The plugin version or "latest" if no version was specified.

    Raises:
        ValueError: If the plugin name is invalid.
    """
    invalid_format_err_msg = (
        f"Invalid plugin name '{plugin_name}'. Expected format: "
        f"`(<author_username>{author_separator})<plugin_name>({version_separator}<version>)`."
    )

    parts = plugin_name.split(version_separator)
    if len(parts) > 2:
        raise ValueError(invalid_format_err_msg)
    name, version = parts[0], "latest" if len(parts) == 1 else parts[1]

    parts = name.split(author_separator)
    if len(parts) > 2:
        raise ValueError(invalid_format_err_msg)
    name, author = parts[-1], None if len(parts) == 1 else parts[0]

    if not name:
        raise ValueError(invalid_format_err_msg)

    return author, name, version


def plugin_display_name(
    name: str, version: Optional[str], author: Optional[str]
) -> str:
    """Helper function to get the display name of a plugin.

    Args:
        name: Name of the plugin.
        version: Version of the plugin.
        author: Username of the plugin author.

    Returns:
        Display name of the plugin.
    """
    author_prefix = ""
    if author and author != ZENML_HUB_ADMIN_USERNAME:
        author_prefix = f"{author}/"
    version_suffix = f":{version}" if version else ":latest"
    return f"{author_prefix}{name}{version_suffix}"
