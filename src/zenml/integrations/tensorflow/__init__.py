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
"""Initialization for TensorFlow integration."""

from zenml.integrations.constants import TENSORFLOW
from zenml.integrations.integration import Integration


class TensorflowIntegration(Integration):
    """Definition of Tensorflow integration for ZenML."""

    NAME = TENSORFLOW
    REQUIREMENTS = [
        "tensorflow==2.8.0",
        "tensorflow_io==0.24.0",
        "protobuf>=3.6.0,<4.0.0",
    ]

    @classmethod
    def activate(cls) -> None:
        """Activates the integration."""
        # need to import this explicitly to load the Tensorflow file IO support
        # for S3 and other file systems
        import tensorflow_io  # type: ignore [import]

        from zenml.integrations.tensorflow import materializers  # noqa


TensorflowIntegration.check_installation()
