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
"""Orchestrator for simple GCP VM backend"""

import base64
import json
import os
import time
from typing import Dict, Any
from typing import Text

import googleapiclient.discovery
from google.oauth2 import service_account as sa

from zenml.backends.orchestrator import OrchestratorBaseBackend
from zenml.repo import Repository
from zenml.standards import standard_keys as keys
from zenml.utils import path_utils
from zenml.utils import requirement_utils
from zenml.constants import ZENML_BASE_IMAGE_NAME, \
    ZENML_TRAINER_IMAGE_NAME, GCP_ENTRYPOINT
from zenml.logger import get_logger

requirement_utils.check_integration(requirement_utils.GCP_INTEGRATION)

logger = get_logger(__name__)

EXTRACTED_TAR_DIR_NAME = 'zenml_working'
TAR_PATH_ARG = 'tar_path'
STAGING_AREA = 'staging'


class OrchestratorGCPBackend(OrchestratorBaseBackend):
    """
    Orchestrates pipeline in a GCP Compute Instance.

    This orchestrator creates a .tar.gz of the current ZenML repository, sends
    it over to the artifact store, then launches a VM with the specified image.
    After pipeline is done, the VM automatically gets brought down, regardless
    of whether the pipeline failed or not. To see logs of the pipeline, use
    Logs Explorer <https://console.cloud.google.com/logs/> and filter for
    `logName="projects/<project_name>/logs/gcplogs-docker-driver"`. After
    running the VM, the logger returns the link directly to the logs.
    """

    def __init__(self,
                 project,
                 cloudsql_connection_name,
                 machine_type: Text = 'e2-medium',
                 gpu: Text = None,
                 gpu_count: int = 0,
                 zone: Text = 'europe-west1-b',
                 instance_name: Text = None,
                 disk_size: int = 100,
                 image: Text = None,
                 source_disk_image: Text = None,
                 preemptible: bool = True,
                 service_account: Text = None):
        """
        Initialize a GCP VM to orchestrate a pipeline. Users have the option
        to run it with or without a GPU. In cases where a GPU is used,
        the `image` and `source_disk_image` are both adapted to be
        CUDA-compatible. This is convenient for the `TrainingPipeline`
        especially.

        Example:
            a) Without GPU:
            ```
            OrchestratorGCPBackend(
                project='my_project_id',
                cloudsql_connection_name='my_project_id:my_region:conn_name'
                machine_type='e2-medium'
            )
            ```
            In the above case, a smaller `image` is used for the
            orchestration of the pipeline, so the load-up time is faster. Use
            for smaller datasets or where a GPU is not required for speed-up
            training.

            b) With GPU:
            ```
            OrchestratorGCPBackend(
                project='my_project_id',
                cloudsql_connection_name='my_project_id:my_region:conn_name'
                machine_type='n1-standard-4',
                gpu='nvidia-tesla-k80',
            )
            ```
            Here, a large `image` is used for orchestration of the pipeline.
            The attached k80 GPU is leveraged for faster training. Note that
            not all machine_type are compatible with attached GPU! Make sure
            to check Google Cloud Platform documentation for a full list.

        Args:
            project: GCP project_id.
            cloudsql_connection_name: Cloud SQL instance name in the form
            {GCP_PROJECT}:{GCP_REGION}:{GCP_CLOUD_SQL_INSTANCE_NAME}

            gpu: (optional) GPU type to attach to VM. If gpu is specified,
            default `image` and `source_disk_image` are both modified. Full
            list of options [here](
            https://cloud.google.com/compute/docs/gpus/create-vm-with-gpus
            #gcloud_1)
            zone: The zone where VM is launched.
            instance_name: Name of the instance.
            disk_size: Size (in GB) of disk to be used.
            preemptible: Set True to use preemtible instance for reduced costs.
            image: The image in which the pipeline actually runs.
            machine_type: VM Machine type. Full list [here](
            https://cloud.google.com/compute/docs/machine-types)
            source_disk_image: The image of the underlying VM.
            service_account: Optional path to service account json file.
        """
        self.project = project
        self.cloudsql_connection_name = cloudsql_connection_name
        self.zone = zone
        self.image = image
        self.machine_type = machine_type
        self.preemptible = preemptible

        if instance_name is None:
            self.instance_name = 'zenml-' + str(int(time.time()))
        else:
            self.instance_name = instance_name

        self.gpu = gpu
        self.gpu_count = gpu_count

        if service_account:
            scopes = ['https://www.googleapis.com/auth/cloud-platform']
            self.credentials = \
                sa.Credentials.from_service_account_file(
                    service_account, scopes=scopes)
        else:
            self.credentials = None

        # Resolve images based on GPU
        if image is None:
            # use gpu image if a gpu is attached
            if self.gpu is None:
                self.image = ZENML_BASE_IMAGE_NAME
            else:
                self.image = ZENML_TRAINER_IMAGE_NAME

        if source_disk_image is None:
            compute = self._get_compute()
            if self.gpu is None:
                # get latest image from cos-85-lts family. As of Jan 28 2021
                # it is: cos-85-13310-1041-38
                image_response = compute.images().getFromFamily(
                    project='cos-cloud',
                    family='cos-85-lts').execute()
                source_disk_image = image_response['selfLink']
            else:
                # get latest image from common-dl family. As of Jan 28 2021
                # it is: 'c0-deeplearning-common-cu110-v20210121-debian-10'
                image_response = compute.images().getFromFamily(
                    project='deeplearning-platform-release',
                    family='common-cu110').execute()
                source_disk_image = image_response['selfLink']

        self.source_disk_image = source_disk_image
        self.disk_size = disk_size

        super().__init__(
            project=project,
            cloudsql_connection_name=cloudsql_connection_name,
            image=image,
            zone=zone,
            instance_name=instance_name,
            machine_type=machine_type,
            preemptible=preemptible,
            service_account=service_account,
            gpu=gpu,
            disk_size=disk_size,
            source_disk_image=source_disk_image,
            gpu_count=gpu_count,
        )

    def launch_instance(self, config: Dict[Text, Any]):
        """
        This function launches a GCP compute instance.

        Args:
            config: a ZenML config dict
        """
        # Instantiate google compute service

        # Configure the machine
        machine_type = f"zones/{self.zone}/machineTypes/{self.machine_type}"
        s_script_name = 'startup-script-gpu.sh' if self.gpu else \
            'startup-script.sh'
        startup_script = open(os.path.join(
            os.path.dirname(__file__), s_script_name), 'r').read()

        config_encoded = base64.b64encode(json.dumps(config).encode())
        c_params = f'python -m {GCP_ENTRYPOINT} run_pipeline --config_b64 ' \
                   f'{config_encoded}'

        compute_config = {
            "kind": "compute#instance",
            'name': self.instance_name,
            'zone': f'projects/{self.project}/zones/{self.zone}',
            'machineType': machine_type,
            "displayDevice": {
                "enableDisplay": False
            },
            # Specify if preemtible
            'scheduling': {'preemptible': self.preemptible},

            # Specify the boot disk and the image to use as a source.
            'disks': [
                {
                    "kind": "compute#attachedDisk",
                    'boot': True,
                    'autoDelete': True,
                    'initializeParams': {
                        'sourceImage': self.source_disk_image,
                        'diskSizeGb': str(self.disk_size)
                    }
                }
            ],

            # Specify a network interface with NAT to access the public
            # internet.
            'networkInterfaces': [{
                "kind": "compute#networkInterface",
                'network': 'global/networks/default',
                'accessConfigs': [
                    {"kind": "compute#accessConfig", 'type': 'ONE_TO_ONE_NAT',
                     'name': 'External NAT'}
                ]
            }],

            # Allow the instance to access cloud storage and logging.
            "serviceAccounts": [
                {
                    "email": "default",
                    "scopes": [
                        "https://www.googleapis.com/auth/cloud-platform",
                        "https://www.googleapis.com/auth/sqlservice.admin"
                    ]
                }
            ],

            # Metadata is readable from the instance and allows you to
            # pass configuration from deployment scripts to instances.
            'metadata': {
                "kind": "compute#metadata",
                'items': [
                    {
                        # Startup script is automatically executed by the
                        # instance upon startup.
                        'key': 'startup-script',
                        'value': startup_script
                    },
                    {
                        'key': 'image_name',
                        'value': self.image,
                    },
                    {
                        'key': 'container_params',
                        'value': c_params,
                    },
                    {
                        'key': 'mlmd_target',
                        'value': self.cloudsql_connection_name,
                    }
                ]
            }
        }

        if self.gpu:
            compute_config["guestAccelerators"] = [
                {
                    "acceleratorCount": self.gpu_count,
                    "acceleratorType":
                        f"projects/{self.project}/zones/{self.zone}"
                        f"/acceleratorTypes/{self.gpu}"
                }
            ]

        logger.info(
            f'Launching instance {self.instance_name} of type '
            f'{self.machine_type} in project: {self.project} in zone '
            f'{self.zone}')

        try:
            compute = self._get_compute()
            res = compute.instances().insert(
                project=self.project,
                zone=self.zone,
                body=compute_config).execute()
        except Exception as e:
            raise AssertionError(f"GCP VM failed to launch with the following "
                                 f"error: {str(e)}")

        logger.info(f'Launched instance {self.instance_name} with ID: '
                    f'{res["targetId"]}')
        log_link = \
            f'https://console.cloud.google.com/logs/query;query=logName%3D' \
            f'%22projects%2F{self.project}%2Flogs%2Fgcplogs-docker-driver%22' \
            f'%0Aresource.labels.instance_id%3D%22' \
            f'{res["targetId"]}%22?' \
            f'project={self.project}&folder=true&query=%0A'
        logger.info(f"View logs at: {log_link}")
        return res

    def run(self, config: Dict[Text, Any]):
        """
        This run function essentially calls an underlying TFX orchestrator run.
        However it is meant as a higher level abstraction with some
        opinionated decisions taken.

        Args:
            config: a ZenML config dict
        """
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

        # Remove tar
        path_utils.rm_dir(path_to_tar)
        logger.info(f'Removed tar at: {path_to_tar}')

        # Append path of tar in config orchestrator utils
        config[keys.GlobalKeys.BACKEND][keys.BackendKeys.ARGS][
            TAR_PATH_ARG] = store_path_to_tar

        # Launch the instance
        self.launch_instance(config)

    def _get_compute(self):
        return googleapiclient.discovery.build(
            'compute', 'v1', credentials=self.credentials)
