#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import os
from typing import Any, Type

from whylogs import DatasetProfile  # type: ignore
from whylogs.whylabs_client.wrapper import upload_profile  # type: ignore

from zenml.artifacts import StatisticsArtifact
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

PROFILE_FILENAME = "profile.pb"


class WhylogsMaterializer(BaseMaterializer):
    """Materializer to read/write whylogs dataset profiles."""

    ASSOCIATED_TYPES = (DatasetProfile,)
    ASSOCIATED_ARTIFACT_TYPES = (StatisticsArtifact,)

    def handle_input(self, data_type: Type[Any]) -> DatasetProfile:
        """Reads and returns a whylogs DatasetProfile.

        Returns:
            A loaded whylogs DatasetProfile.
        """
        super().handle_input(data_type)
        filepath = os.path.join(self.artifact.uri, PROFILE_FILENAME)
        with fileio.open(filepath, "rb") as f:
            protobuf = DatasetProfile.parse_delimited(f.read())[0]
        return protobuf

    def handle_return(self, profile: DatasetProfile) -> None:
        """Writes a whylogs DatasetProfile.

        Args:
            profile: A DatasetProfile object from whylogs.
        """
        super().handle_return(profile)
        filepath = os.path.join(self.artifact.uri, PROFILE_FILENAME)
        protobuf = profile.serialize_delimited()
        with fileio.open(filepath, "wb") as f:
            f.write(protobuf)

        # TODO [ENG-439]: uploading profiles to whylabs should be enabled and
        #  configurable at step level or pipeline level instead of being
        #  globally enabled.
        if os.environ.get("WHYLABS_DEFAULT_ORG_ID"):
            upload_profile(profile)
