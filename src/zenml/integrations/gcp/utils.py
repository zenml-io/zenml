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
"""GCP utils."""

import re


def sanitize_vertex_label(value: str) -> str:
    """Sanitize a label value to comply with Vertex AI requirements.

    Args:
        value: The label value to sanitize

    Returns:
        Sanitized label value
    """
    if not value:
        return ""

    # Convert to lowercase
    value = value.lower()

    # Replace any character that's not lowercase letter, number, dash or underscore
    value = re.sub(r"[^a-z0-9\-_]", "-", value)

    # Ensure it starts with a letter/number by prepending 'x' if needed
    if not value[0].isalnum():
        value = f"x{value}"

    # Truncate to 63 chars to stay under limit
    return value[:63]
