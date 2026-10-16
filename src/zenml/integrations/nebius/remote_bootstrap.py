#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Execute the unmodified ZenML argv without shell interpolation."""

import json
import os
import sys
from pathlib import Path
from typing import List

ARGV_PATH = "/opt/zenml-nebius-argv.json"
MAX_ARGV_BYTES = 65536


def encode_argv(command: List[str]) -> bytes:
    """Validate and encode the command for a Nebius injected file.

    Args:
        command: The exact command supplied by ZenML.

    Returns:
        UTF-8 JSON suitable for file injection.

    Raises:
        ValueError: If argv is invalid or exceeds the provider's file limit.
    """
    if (
        not command
        or not command[0]
        or any(not isinstance(arg, str) or "\0" in arg for arg in command)
    ):
        raise ValueError(
            "Nebius requires a nonempty argv with no NUL characters."
        )
    payload = json.dumps(command, ensure_ascii=False).encode("utf-8")
    if len(payload) > MAX_ARGV_BYTES:
        raise ValueError(
            "Nebius entrypoint argv exceeds the 64 KiB injected-file limit."
        )
    return payload


def main() -> None:
    """Replace this process with the standard ZenML step entrypoint.

    Raises:
        ValueError: If the injected command is malformed or too large.
    """
    path = Path(sys.argv[1] if len(sys.argv) == 2 else ARGV_PATH)
    with path.open("rb") as file:
        payload = file.read(MAX_ARGV_BYTES + 1)
    if len(payload) > MAX_ARGV_BYTES:
        raise ValueError("Injected argv exceeds 64 KiB.")
    command = json.loads(payload)
    if not isinstance(command, list):
        raise ValueError("Injected argv must be a list.")
    encode_argv(command)
    os.execvpe(command[0], command, os.environ)


if __name__ == "__main__":
    main()
