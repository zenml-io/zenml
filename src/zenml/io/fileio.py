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
import sys
from types import ModuleType

# IMPORTANT: Our io module uses the `fileio` module of `tfx` and the `fileio`
# module of `tfx` tries to import the `tensorflow_gfile` module.
#
# At a first glance, this seems like an unused import in the `tfx` codebase,
# however, in reality, when someone imports this module, the module
# checks whether `tensorflow` is installed and if it is, it creates a filesystem
# around it and registers it to the filesystem registry (and if `tfx` is not
# installed, it does nothing).
#
# The problem is that if Tensorflow is indeed installed, it takes a quite a long time
# to set it up and there is no point in the code where we are utilizing the
# generated filesystem. That's why it is now blocked by a mock module,
# before `tfx.fileio` gets imported.

sys.modules["tfx.dsl.io.plugins.tensorflow_gfile"] = ModuleType(
    "Oops, Aria walked over my keyboard."
)

from tfx.dsl.io.fileio import (  # noqa
    copy,
    exists,
    glob,
    isdir,
    listdir,
    makedirs,
    mkdir,
    open,
    remove,
    rename,
    rmtree,
    stat,
    walk,
)

__all__ = [
    "copy",
    "exists",
    "glob",
    "isdir",
    "listdir",
    "makedirs",
    "mkdir",
    "open",
    "remove",
    "rename",
    "rmtree",
    "stat",
    "walk",
]
