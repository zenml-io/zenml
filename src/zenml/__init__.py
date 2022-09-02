#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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
"""Initialization for ZenML."""

import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(ROOT_DIR, "VERSION")) as version_file:
    __version__: str = version_file.read().strip()

from zenml.logger import init_logging  # noqa

init_logging()

# Try to import the LocalZenServer here because it needs to be registered in the
# service registry early on in order to be available for use in other modules.
# If the LocalZenServer dependencies aren't installed, there is no need to register
# it anywhere so we simply pass.
try:
    from zenml.zen_server.deploy.local.local_zen_server import LocalZenServer
except ImportError:
    pass

# Try to import the DockerZenServer here because it needs to be registered in the
# service registry early on in order to be available for use in other modules.
try:
    from zenml.zen_server.deploy.docker.docker_zen_server import DockerZenServer
except ImportError:
    pass
