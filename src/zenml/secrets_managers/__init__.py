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
## Secret Manager

Most projects involving either cloud infrastructure or of a certain complexity
will involve secrets of some kind. For example, you'll use secrets to connecting
to AWS, which requires an `access_key_id` and a `secret_access_key`. On your
local machine this is usually stored in your `~/.aws/credentials` file.

You might find you need to access those secrets from within your Kubernetes
cluster as it runs individual steps. You might also just want a centralized
location for the storage of secrets across your ZenML project. 

ZenML gives you all this with the Secret Manager stack component.
"""
from zenml.secrets_managers.base_secrets_manager import BaseSecretsManager
from zenml.secrets_managers.local.local_secrets_manager import (
    LocalSecretsManager,
)

__all__ = [
    "BaseSecretsManager",
    "LocalSecretsManager",
]
