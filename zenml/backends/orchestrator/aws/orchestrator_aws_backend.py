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
from typing import Text, Dict, Any

from zenml.backends.orchestrator.aws import utils
from zenml.backends.orchestrator import OrchestratorBaseBackend
from zenml.repo import Repository
from zenml.standards import standard_keys as keys
from zenml.utils import path_utils
from zenml.constants import ZENML_BASE_IMAGE_NAME
from zenml.logger import get_logger

logger = get_logger(__name__)

EXTRACTED_TAR_DIR_NAME = 'zenml_working'
STAGING_AREA = 'staging'
TAR_PATH_ARG = 'tar_path'


class OrchestratorAWSBackend(OrchestratorBaseBackend):
    """
    Orchestrates pipeline on a AWS EC2 instance
    """

    def __init__(self,
                 iam_role: Text,
                 instance_type: Text = 't2.micro',
                 instance_image: Text = 'ami-02e9f4e447e4cda79',
                 zenml_image: Text = None,
                 region: Text = None,
                 key_name: Text = None,
                 security_group: Text = None,
                 min_count: int = 1,
                 max_count: int = 1):
        """
        Base class for the orchestrator backend on AWS

        :param iam_role: the name of the role created in AWS IAM
        :param instance_type: the type of the EC2 instance, defaults to
        t2.micro
        :param instance_image: the image for the EC2 instance, defaults to the
        public image: Deep Learning AMI (Amazon Linux 2) Version 39.0
        :param zenml_image: refers to the image with ZenML
        :param region: the name of the region that AWS is working on
        :param key_name: the name of the key to be used whilst creating the
        instance on EC2
        :param security_group: the name of a selected security group
        :param min_count: the minimum number of instances, defaults to 1
        :param max_count: the maximum number of instances, defaults to 1
        """

        self.session = utils.setup_session()
        self.region = utils.setup_region(region)

        self.ec2_client = self.session.client('ec2')
        self.ec2_resource = self.session.resource('ec2')

        self.instance_type = instance_type
        self.instance_image = instance_image
        self.zenml_image = zenml_image
        self.key_name = key_name
        self.min_count = min_count
        self.max_count = max_count

        if security_group is not None:
            self.security_group = [security_group]
        else:
            self.security_group = security_group

        self.iam_role = {'Name': iam_role}

        if zenml_image is None:
            self.zenml_image = ZENML_BASE_IMAGE_NAME
        else:
            self.zenml_image = zenml_image

        super(OrchestratorBaseBackend, self).__init__(
            instance_type=self.instance_type,
            instance_image=self.instance_image,
            zenml_image=self.zenml_image,
            region=self.region,
            key_name=self.key_name,
            min_count=self.min_count,
            max_count=self.max_count,
            security_group=self.security_group,
            iam_role=self.iam_role,
        )

    @staticmethod
    def make_unique_name(name):
        return f'{name}-{time.asctime()}'

    def launch_instance(self, config):
        startup = utils.get_startup_script(config,
                                           self.region,
                                           self.zenml_image)

        args = {'ImageId': self.instance_image,
                'InstanceType': self.instance_type,
                'IamInstanceProfile': self.iam_role,
                'MaxCount': self.max_count,
                'MinCount': self.min_count,
                'UserData': startup}

        if self.security_group:
            args['SecurityGroups'] = self.security_group

        if self.key_name:
            args['KeyName'] = self.key_name

        return self.ec2_resource.create_instances(**args)

    def run(self, config: [Dict, Any]):
        # Extract the paths to create the tar
        logger.info('Orchestrating pipeline on AWS..')

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

        # Remove tar
        path_utils.rm_dir(path_to_tar)
        logger.info(f'Removed tar at: {path_to_tar}')

        # Append path of tar in config orchestrator utils
        config[keys.GlobalKeys.BACKEND][keys.BackendKeys.ARGS][
            TAR_PATH_ARG] = store_path_to_tar

        # Launch the instance
        self.launch_instance(config)
