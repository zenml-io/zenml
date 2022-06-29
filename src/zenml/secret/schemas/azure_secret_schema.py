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
"""Azure Authentication Secret Schema definition."""

from typing import ClassVar, Optional

from zenml.secret.base_secret import BaseSecretSchema

AZURE_SECRET_SCHEMA_TYPE = "azure"


class AzureSecretSchema(BaseSecretSchema):
    """Azure Authentication Secret Schema definition."""

    TYPE: ClassVar[str] = AZURE_SECRET_SCHEMA_TYPE

    # Azure key vault store doesn't permit the use of underscores
    # for key names, so we use them without here but reconstitute
    # them where they are used elsewhere for authentication.
    # (e.g. in the artifact store)
    accountname: Optional[str] = None
    accountkey: Optional[str] = None
    sastoken: Optional[str] = None
    connectionstring: Optional[str] = None
    clientid: Optional[str] = None
    clientsecret: Optional[str] = None
    tenantid: Optional[str] = None
