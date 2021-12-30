#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

from whylogs.app.session import Session
from whylogs.app.session import load_config, session_from_config

from zenml.artifacts import StatisticsArtifact
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "profile.pb"
DEFAULT_PROJECT_NAME = "project"
DEFAULT_PIPELINE_NAME = "pipeline"
CONFIG_NAME = 'config.yaml'

CONFIG = f"""
project: {DEFAULT_PROJECT_NAME}
pipeline: {DEFAULT_PIPELINE_NAME}
verbose: false
"""


class WhylogsMaterializer(BaseMaterializer):
    """Materializer to read/write Pytorch models."""

    ASSOCIATED_TYPES = [Session]
    ASSOCIATED_ARTIFACT_TYPES = [StatisticsArtifact]

    def handle_input(self, data_type: Type[Any]) -> Session:
        """Reads and returns a Session.

        Returns:
            A loaded Session.
        """
        super().handle_input(data_type)
        config_path = os.path.join(self.artifact.uri, CONFIG_NAME)
        session = session_from_config(config_path)
        session.log_dataframe()
        return Session.read_protobuf(
            os.path.join(self.artifact.uri, DEFAULT_FILENAME)
        )

    def handle_return(self, session: Session) -> None:
        """Writes a Session.

        Args:
            session: A Session object from whylogs.
        """
        super().handle_return(session)
        session = session_from_config(config_path)
        session.close()
        profile.write_protobuf(
            os.path.join(self.artifact.uri, DEFAULT_FILENAME)
        )
