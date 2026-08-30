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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Identity shared by independently fenced execution archive workers."""

import os
import socket
from uuid import uuid4


def new_execution_archive_worker_id() -> str:
    """Return a process-local identity unique to one worker instance.

    Returns:
        Host, process, and random worker identity.
    """
    return f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}"
