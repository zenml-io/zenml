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
"""Implementation of a ZenML ServiceType class."""

from pydantic import BaseModel


class ServiceType(BaseModel):
    """Service type descriptor.

    Attributes:
        type: service type
        flavor: service flavor
        name: name of the service type
        description: description of the service type
        logo_url: logo of the service type
    """

    type: str
    flavor: str
    name: str = ""
    description: str = ""
    logo_url: str = ""

    class Config:
        """Pydantic configuration class."""

        # make the service type immutable and hashable
        frozen = True
