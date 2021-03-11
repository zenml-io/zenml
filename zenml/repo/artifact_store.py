#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
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
"""Definition of an Artifact Store"""

import hashlib
import os
from typing import Text

from zenml.repo import GlobalConfig
from zenml.utils import path_utils
from zenml.enums import ArtifactStoreTypes
from zenml.utils.print_utils import to_pretty_string, PrintStyles


class ArtifactStore:
    """Base class for all ZenML datasources.

    Every ZenML datasource should override this class.
    """

    def __init__(self, path: Text):
        self.path = path

        if path_utils.is_gcs_path(path):
            self.store_type = ArtifactStoreTypes.gcs.name
        else:
            self.store_type = ArtifactStoreTypes.local.name

        # unique_id based on path should be globally consistent
        self.unique_id = hashlib.md5(self.path.encode()).hexdigest()

    def __str__(self):
        return to_pretty_string(self.path)

    def __repr__(self):
        return to_pretty_string(self.path, style=PrintStyles.PPRINT)

    @staticmethod
    def get_component_name_from_uri(artifact_uri: Text):
        """
        Gets component name from artifact URI.

        Args:
            artifact_uri (str): URI to artifact.
        """
        return path_utils.get_grandparent(artifact_uri)

    def resolve_uri_locally(self, artifact_uri: Text, path: Text = None):
        """
        Takes a URI that points within the artifact store, downloads the
        URI locally, then returns local URI.

        Args:
            artifact_uri: uri to artifact.
            path: optional path to download to. If None, is inferred.
        """
        if not path_utils.is_remote(artifact_uri):
            # Its already local
            return artifact_uri

        if path is None:
            # Create a unique path in local machine
            path = os.path.join(
                GlobalConfig.get_config_dir(),
                self.unique_id,
                ArtifactStore.get_component_name_from_uri(artifact_uri),
                path_utils.get_parent(artifact_uri)  # unique ID from MLMD
            )

        # Create if not exists and download
        path_utils.create_dir_recursive_if_not_exists(path)
        path_utils.copy_dir(artifact_uri, path, overwrite=True)

        return path
