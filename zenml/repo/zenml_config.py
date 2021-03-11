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
"""Functions to handle ZenML config"""

import os
from typing import Text, Optional, Dict, Type

from zenml.metadata import ZenMLMetadataStore
from zenml.repo import ArtifactStore
from zenml.repo.constants import ZENML_CONFIG_NAME, \
    ARTIFACT_STORE_DEFAULT_DIR, PIPELINES_DEFAULT_DIR_NAME, \
    ML_METADATA_SQLITE_DEFAULT_NAME, ZENML_DIR_NAME
from zenml.standards import standard_keys as keys
from zenml.utils import path_utils, yaml_utils
from zenml.exceptions import InitializationException

ARTIFACT_STORE_KEY = keys.GlobalKeys.ARTIFACT_STORE
METADATA_KEY = keys.GlobalKeys.METADATA_STORE
PIPELINES_DIR_KEY = 'pipelines_dir'


class ZenMLConfig:
    """ZenML config class to handle config operations.

    This is an internal class and should not be used by the user.
    """

    def __init__(self, repo_path: Text):
        """
        Construct class instance for ZenML Config.

        Args:
            repo_path (str): path to root of repository.
        """
        self.repo_path = repo_path
        if not ZenMLConfig.is_zenml_dir(self.repo_path):
            raise InitializationException(
                f'This is not a ZenML repository, as it does '
                f'not contain the {ZENML_CONFIG_NAME} '
                f'config file. Please initialize your repo '
                f'with `zenml init` with the ZenML CLI.')

        self.config_dir = os.path.join(repo_path, ZENML_DIR_NAME)
        self.config_path = os.path.join(self.config_dir, ZENML_CONFIG_NAME)

        self.raw_config = yaml_utils.read_yaml(self.config_path)

        # Load self vars in init to be clean
        self.metadata_store: Optional[ZenMLMetadataStore] = None
        self.artifact_store: Optional[ArtifactStore] = None
        self.pipelines_dir: Text = ''

        # Override these using load_config
        self.from_config(self.raw_config)

    @staticmethod
    def is_zenml_dir(path: Text):
        """
        Check if dir is a zenml dir or not.

        Args:
            path (str): path to the root.
        """
        config_path = os.path.join(path, ZENML_DIR_NAME, ZENML_CONFIG_NAME)
        if not path_utils.file_exists(config_path):
            return False
        return True

    @staticmethod
    def to_config(path: Text,
                  artifact_store_path: Text = None,
                  metadata_store: Optional[Type[ZenMLMetadataStore]] = None,
                  pipelines_dir: Text = None):
        """
        Creates a default .zenml config at path/zenml/.zenml_config.

        Args:
            path (str): path to a directory.
            metadata_store: metadata store definition.
            artifact_store_path (str): path where to store artifacts.
            pipelines_dir (str): path where to store pipeline configs.
        """
        config_dir_path = os.path.join(path, ZENML_DIR_NAME)
        config_path = os.path.join(config_dir_path, ZENML_CONFIG_NAME)

        if path_utils.file_exists(config_path):
            raise AssertionError(f'.zenml file already exists at '
                                 f'{config_path}. '
                                 f'Cannot replace. Please delete the '
                                 f'{config_dir_path} directory first.')

        # Create config dir
        path_utils.create_dir_if_not_exists(config_dir_path)

        if artifact_store_path is None:
            artifact_store_path = \
                os.path.join(config_dir_path, ARTIFACT_STORE_DEFAULT_DIR)
        else:
            # if provided, then resolve it absolutely
            artifact_store_path = path_utils.resolve_relative_path(
                artifact_store_path)

        # create artifact_store path
        path_utils.create_dir_if_not_exists(artifact_store_path)

        if metadata_store is None:
            uri = os.path.join(
                artifact_store_path, ML_METADATA_SQLITE_DEFAULT_NAME)
            from zenml.metadata import \
                SQLiteMetadataStore
            metadata_dict = SQLiteMetadataStore(uri).to_config()
        else:
            metadata_dict = metadata_store.to_config()

        if pipelines_dir is None:
            pipelines_dir = os.path.join(path, PIPELINES_DEFAULT_DIR_NAME)
        else:
            # if provided, still resolve
            pipelines_dir = path_utils.resolve_relative_path(pipelines_dir)

        path_utils.create_dir_if_not_exists(pipelines_dir)
        config_dict = {
            ARTIFACT_STORE_KEY: artifact_store_path,
            METADATA_KEY: metadata_dict,
            PIPELINES_DIR_KEY: pipelines_dir,
        }
        # Write initial config
        yaml_utils.write_yaml(config_path, config_dict)

    def from_config(self, config_dict: Dict):
        """
        Sets metadata and artifact_store variables

        Args:
            config_dict (dict): .zenml config object in dict format.
        """
        assert METADATA_KEY in config_dict
        assert ARTIFACT_STORE_KEY in config_dict
        assert PIPELINES_DIR_KEY in config_dict

        self.artifact_store = ArtifactStore(config_dict[ARTIFACT_STORE_KEY])
        self.metadata_store = ZenMLMetadataStore.from_config(
            config=config_dict[METADATA_KEY]
        )
        self.pipelines_dir = config_dict[PIPELINES_DIR_KEY]

    def get_metadata_store(self) -> ZenMLMetadataStore:
        """Get metadata store from config."""
        return self.metadata_store

    def get_artifact_store(self) -> ArtifactStore:
        """Get artifact store from config"""
        return self.artifact_store

    def get_pipelines_dir(self) -> Text:
        """Get absolute path of pipelines dir from config"""
        return self.pipelines_dir

    def set_artifact_store(self, artifact_store_path: Text):
        """
        Updates artifact store to point to path.

        Args:
            artifact_store_path: new path to artifact store
        """
        self.artifact_store = ArtifactStore(artifact_store_path)
        self.save()

    def set_metadata_store(self, metadata_store: ZenMLMetadataStore):
        """
        Updates artifact store to point to path.

        Args:
            metadata_store: metadata store
        """
        self.metadata_store = metadata_store
        self.save()

    def set_pipelines_dir(self, pipelines_dir: Text):
        """
        Updates artifact store to point to path.

        Args:
            pipelines_dir: new path to pipelines dir
        """
        path_utils.create_dir_if_not_exists(pipelines_dir)
        self.pipelines_dir = pipelines_dir
        self.save()

    def save(self):
        config_dict = {
            ARTIFACT_STORE_KEY: self.artifact_store.path,
            METADATA_KEY: self.metadata_store.to_config(),
            PIPELINES_DIR_KEY: self.pipelines_dir,
        }

        # Write initial config
        yaml_utils.write_yaml(self.config_path, config_dict)
