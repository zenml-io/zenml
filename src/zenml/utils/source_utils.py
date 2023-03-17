#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Utility functions for source code.

These utils are predicated on the following definitions:

* class_source: This is a python-import type path to a class, e.g.
    some.mod.class
* module_source: This is a python-import type path to a module, e.g. some.mod
* file_path, relative_path, absolute_path: These are file system paths.
* source: This is a class_source or module_source. If it is a class_source, it
    can also be optionally pinned.
* pin: Whatever comes after the `@` symbol from a source, usually the git sha
    or the version of zenml as a string.
"""
from typing import (
    TYPE_CHECKING,
    Optional,
)

from zenml.logger import get_logger

if TYPE_CHECKING:
    pass


logger = get_logger(__name__)

_CUSTOM_SOURCE_ROOT: Optional[str] = None
