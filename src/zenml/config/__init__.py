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
"""The `config` module contains classes and functions that manage user-specific configuration.

ZenML's configuration is stored in a file called
``config.yaml``, located on the user's directory for configuration files.
(The exact location differs from operating system to operating system.)

The ``GlobalConfiguration`` class is the main class in this module. It provides
a Pydantic configuration object that is used to store and retrieve
configuration. This ``GlobalConfiguration`` object handles the serialization and
deserialization of the configuration options that are stored in the file in
order to persist the configuration across sessions.
"""
from zenml.config.docker_settings import DockerSettings
from zenml.config.resource_settings import ResourceSettings

__all__ = [
    "DockerSettings",
    "ResourceSettings",
]
