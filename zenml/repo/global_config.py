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
"""Global config for the ZenML installation."""

import os
from uuid import uuid4

import click

from zenml import constants
from zenml.utils import path_utils
from zenml.utils import yaml_utils


# TODO: [MEDIUM] Optimize the reads and writes of this

class GlobalConfig(dict):
    """Class definition for the global config."""
    __instance__ = None

    def __init__(self, *args, **kwargs):
        """
        This is a Singleton class.

        Args:
            *args:
            **kwargs:
        """
        if GlobalConfig.__instance__ is None:
            self.path = os.path.join(
                GlobalConfig.get_config_dir(), 'info.json')
            # Create default global config if it does not exist.
            path_utils.create_dir_recursive_if_not_exists(
                GlobalConfig.get_config_dir())

            if path_utils.file_exists(self.path):
                # Load the config
                self.load()
            else:
                # Set up a default config
                # True by default but user is always asked
                self['analytics_opt_in'] = True

            # Create user ID will save the whole thing
            self.user_id = self.create_user_id()

            super(GlobalConfig, self).__init__(*args, **kwargs)
            GlobalConfig.__instance__ = self
        else:
            raise Exception("You cannot create another GlobalConfig class!")

    @staticmethod
    def get_instance():
        """ Static method to fetch the current instance."""
        if not GlobalConfig.__instance__:
            GlobalConfig()
        return GlobalConfig.__instance__

    @staticmethod
    def get_config_dir():
        """Gets config dir."""
        return click.get_app_dir(constants.APP_NAME)

    def create_user_id(self):
        """Creates user_id if it does not exist."""
        if 'user_id' not in self:
            self['user_id'] = str(uuid4())
            self.save()
        return self['user_id']

    def get_user_id(self):
        """Gets user_id from config. If not present, creates a new one."""
        if 'user_id' in self:
            return self['user_id']
        else:
            return self.create_user_id()

    def get_analytics_opt_in(self) -> bool:
        """Gets user_id from config. If not present, creates a new one."""
        if 'analytics_opt_in' in self:
            return self['analytics_opt_in']
        else:
            # assume False if this variable not found
            return False

    def set_analytics_opt_in(self, toggle: bool):
        """Set opt-in flag for analytics"""
        self.load()
        self['analytics_opt_in'] = toggle
        self.save()

    def load(self):
        """Load from YAML file."""
        # TODO: [LOW] Look at locking mechanism to avoid race conditions.
        try:
            tbu = yaml_utils.read_json(self.path)
        except Exception as e:
            print(str(e))
            tbu = {}
        self.update(tbu)

    def save(self):
        """Save current config to YAML file"""
        yaml_utils.write_json(self.path, self)
