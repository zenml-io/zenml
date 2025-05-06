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
"""Initialization of the S3 integration.

The S3 integration allows the use of cloud artifact stores and file
operations on S3 buckets.
"""
from typing import List, Type

from zenml.integrations.constants import S3
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

S3_ARTIFACT_STORE_FLAVOR = "s3"


class S3Integration(Integration):
    """Definition of S3 integration for ZenML."""

    NAME = S3
    # boto3 isn't required for the filesystem to work, but it is required
    # for the AWS/S3 connector that can be used with the artifact store.
    REQUIREMENTS = [
        # Explicitly exclude 2025.3.1 to avoid pulling in the yanked fsspec
        # package with the same version
        "s3fs>2022.3.0,!=2025.3.1",
        "boto3",
        # The following dependencies are only required for the AWS connector.
        "aws-profile-manager",
    ]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the s3 integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.s3.flavors import S3ArtifactStoreFlavor

        return [S3ArtifactStoreFlavor]

