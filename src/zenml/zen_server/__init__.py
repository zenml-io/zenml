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
"""
The ZenServer is a simple webserver to let you collaborate on stacks via
the network. It can be spun up in a background daemon from the command line
using `zenml server up` and managed from the same command line group.

Using the ZenServer's stacks in your project just requires setting up a
profile with `rest` store-type pointed to the url of the server.
"""

from zenml.zen_server.zen_server import (
    ZenServer,
    ZenServerConfig,
    ZenServerEndpoint,
    ZenServerEndpointConfig,
)

__all__ = [
    "ZenServer",
    "ZenServerConfig",
    "ZenServerEndpoint",
    "ZenServerEndpointConfig",
]
