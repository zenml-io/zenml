#  Copyright (c) maiot GmbH 2021. All Rights Reserved.
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
"""Orchestrator for simple AWS VM backend"""

import os
import time
from typing import Text, List, Dict, Any

import boto3

from zenml.core.repo.repo import Repository
from zenml.core.standards import standard_keys as keys
from zenml.utils import path_utils
from zenml.utils.logger import get_logger

logger = get_logger(__name__)

EXTRACTED_TAR_DIR_NAME = 'zenml_working'
STAGING_AREA = 'staging'


class OrchestratorAWSBackend:
    """
    Orchestrates pipeline on a AWS EC2 instance
    """

    def __init__(self,
                 instance_name: Text = 'zenml',
                 instance_type: Text = 't2.micro',
                 image_id: Text = 'ami-001ec343bb21e7e59',
                 key_name: Text = 'baris',
                 min_count: int = 1,
                 max_count: int = 1,
                 security_groups: List = None,
                 instance_profile: Dict = None):

        self.ec2_resource = boto3.resource('ec2')
        self.ec2_client = boto3.client('ec2')

        self.instance_name = instance_name
        self.instance_type = instance_type
        self.image_id = image_id
        self.key_name = key_name
        self.min_count = min_count
        self.max_count = max_count

        if security_groups is None:
            self.security_groups = ['zenml']
        else:
            self.security_groups = security_groups

        if instance_profile is None:
            self.instance_profile = {'Name': 'ZenML'}
        else:
            self.instance_profile = instance_profile

        self.startup = open(os.path.join(os.path.dirname(__file__),
                                         'startup.sh'), 'r').read()

    @staticmethod
    def make_unique_name(name):
        return f'{name}-{time.asctime()}'

    def get_key_pair_by_name(self,
                             name):
        key_pairs = self.ec2_client.describe_key_pairs()
        key_pair = [kp for kp in key_pairs['KeyPairs'] if
                    kp['KeyName'] == name]
        assert len(key_pair) == 1
        return key_pair[0]

    def create_vm_instance(self):
        return self.ec2_resource.create_instances(
            ImageId=self.image_id,
            InstanceType=self.instance_type,
            SecurityGroups=self.security_groups,
            IamInstanceProfile=self.instance_profile,
            KeyName=self.key_name,
            MaxCount=self.max_count,
            MinCount=self.min_count,
            UserData=self.startup)

    def run(self, config: [Dict, Any]):
        # Extract the paths to create the tar
        logger.info('Orchestrating pipeline on GCP..')

        repo: Repository = Repository.get_instance()
        repo_path = repo.path
        config_dir = repo.zenml_config.config_dir
        tar_file_name = \
            f'{EXTRACTED_TAR_DIR_NAME}_{str(int(time.time()))}.tar.gz'
        path_to_tar = os.path.join(config_dir, tar_file_name)

        # Create tarfile but exclude .zenml folder if exists
        path_utils.create_tarfile(repo_path, path_to_tar)
        logger.info(f'Created tar of current repository at: {path_to_tar}')

        # Upload tar to artifact store
        store_path = config[keys.GlobalKeys.ARTIFACT_STORE]
        store_staging_area = os.path.join(store_path, STAGING_AREA)
        store_path_to_tar = os.path.join(store_staging_area, tar_file_name)
        path_utils.copy(path_to_tar, store_path_to_tar)
        logger.info(f'Copied tar to artifact store at: {store_path_to_tar}')


i = OrchestratorAWSBackend()
# OrchestratorAWSBackend().create_vm_instance()
