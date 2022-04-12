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
The S3 integration allows the use of cloud artifact stores and file
operations on S3 buckets.
"""
from zenml.integrations.constants import S3
from zenml.integrations.integration import Integration


class S3Integration(Integration):
    """Definition of S3 integration for ZenML."""

    NAME = S3
    REQUIREMENTS = ["s3fs==2022.3.0"]

    @classmethod
    def activate(cls) -> None:
        """Activates the integration."""
        from zenml.integrations.s3 import artifact_stores  # noqa


S3Integration.check_installation()
