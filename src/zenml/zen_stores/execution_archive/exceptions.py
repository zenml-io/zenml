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
"""Errors raised while archiving execution history."""

from zenml.exceptions import ArchiveUnavailableError, ZenMLBaseException


class ExecutionArchiveError(ZenMLBaseException):
    """Base class of execution archive errors."""


class ExecutionArchiveStateError(ExecutionArchiveError):
    """Raised when a catalog transition is not allowed from the current state."""


class ChecksumMismatchError(ArchiveUnavailableError):
    """Raised when archived bytes do not match their recorded digest."""


class ArchiveObjectInvalidError(ArchiveUnavailableError):
    """Raised when verified bytes do not contain a valid archive object."""
