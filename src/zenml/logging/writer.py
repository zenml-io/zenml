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
"""Replacement for the stdout during step execution."""

import logging
from io import StringIO

stdout_logger = logging.getLogger("ZenStdOutLogger")


class ZenStdOut(StringIO):
    """A replacement for the sys.stdout to turn outputs into logging entries.

    When used in combination with the ZenHandler, this class allows us to
    capture any print statements or third party outputs as logs and store them
    in the artifact store.

    Right now, this is only used during the execution of a ZenML step.
    """

    def write(self, message: str) -> int:
        """Write the incoming string as an info log entry.

        Args:
            message: the incoming message string,
        """
        if message != "\n":
            stdout_logger.info(message)
        return len(message)
