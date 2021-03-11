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
"""Definition of the Kubernetes Orchestrator Backend"""

import base64
import json
import os
import time
from typing import Dict, Any, Text

from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from kubernetes.config.config_exception import ConfigException

from zenml.backends.orchestrator import OrchestratorBaseBackend
from zenml.repo import Repository
from zenml.standards import standard_keys as keys
from zenml.utils import path_utils
from zenml.constants import ZENML_BASE_IMAGE_NAME, K8S_ENTRYPOINT
from zenml.enums import ImagePullPolicy
from zenml.logger import get_logger
from zenml.utils.string_utils import to_dns1123, get_id

logger = get_logger(__name__)

EXTRACTED_TAR_DIR_NAME = 'zenml_working'
TAR_PATH_ARG = 'tar_path'
STAGING_AREA = 'staging'
DEFAULT_K8S_CONFIG = os.path.join(os.environ["HOME"], '.kube/config')


class OrchestratorKubernetesBackend(OrchestratorBaseBackend):
    """
    Runs pipeline on a Kubernetes cluster.

    This orchestrator creates a .tar.gz of the current ZenML repository, sends
    it over to the artifact store, then launches a job in a Kubernetes cluster
    taken from your environment or specified via a passed-on kubectl config.

    Args:
        image: the Docker Image to be used for this ZenML pipeline
        job_prefix: a custom prefix for your Jobs in Kubernetes
            (default: 'zenml-')
        extra_labels: additional labels for your Jobs in Kubernetes
        extra_annotations: additional annotations for your Jobs in Kubernetes
        namespace: a custom Kubernetes namespace for this pipeline
            (default: 'default')
        image_pull_policy: Kubernetes image pull policy.
            One of ['Always', 'Never', 'IfNotPresent'].
            (default: 'IfNotPresent')
        kubernetes_config_path: Path to your Kubernetes cluster connection
        config.
            (default: '~/.kube/config'
    """

    def __init__(self,
                 image: Text = ZENML_BASE_IMAGE_NAME,
                 job_prefix: Text = 'zenml-',
                 extra_labels: Dict[Text, Any] = None,
                 extra_annotations: Dict[Text, Any] = None,
                 namespace: Text = None,
                 image_pull_policy: Text = ImagePullPolicy.IfNotPresent.name,
                 kubernetes_config_path: Text = DEFAULT_K8S_CONFIG):
        self.image = image
        self.job_prefix = job_prefix
        self.extra_labels = extra_labels  # custom k8s labels
        self.extra_annotations = extra_annotations  # custom k8s annotations
        self.namespace = namespace
        self.image_pull_policy = image_pull_policy
        assert image_pull_policy in ImagePullPolicy.__members__.keys()
        self.kubernetes_config_path = kubernetes_config_path

        super().__init__(
            image=image,
            job_prefix=job_prefix,
            extra_labels=extra_labels,
            extra_annotations=extra_annotations,
            namespace=namespace,
            image_pull_policy=image_pull_policy,
            kubernetes_config_path=kubernetes_config_path,
        )

    def create_job_object(self, config):
        pipeline_name = config[keys.GlobalKeys.PIPELINE][
            keys.PipelineKeys.ARGS][keys.PipelineDetailKeys.NAME]
        job_name = to_dns1123(f'{self.job_prefix}{pipeline_name}', length=63)
        labels = self.extra_labels or {}
        job_labels = {
            "app": "zenml",
            "pipeline": pipeline_name,
            "datasource-id": config[keys.GlobalKeys.PIPELINE][
                keys.PipelineKeys.DATASOURCE][keys.DatasourceKeys.ID],
            "pipeline-id": get_id(pipeline_name)
        }
        labels.update(job_labels)  # make sure our labels are present

        config_encoded = base64.b64encode(json.dumps(config).encode()).decode(
            'utf-8')  # kubernetes needs the config as string

        command = ['python', '-m', K8S_ENTRYPOINT, 'run_pipeline',
                   '--config_b64', config_encoded]

        container = k8s_client.V1Container(
            name=job_name,
            image=self.image,
            command=command,
            image_pull_policy=self.image_pull_policy
        )

        # Create and configure a spec section
        template = k8s_client.V1PodTemplateSpec(
            metadata=k8s_client.V1ObjectMeta(labels=labels),
            spec=k8s_client.V1PodSpec(restart_policy="Never",
                                      containers=[container]))

        # Create the specification of deployment
        spec = k8s_client.V1JobSpec(
            template=template,
            backoff_limit=1)

        # Instantiate the job object
        job = k8s_client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=k8s_client.V1ObjectMeta(
                annotations=self.extra_annotations,
                labels=labels,
                name=job_name,
                namespace=self.namespace),
            spec=spec)

        return job

    def launch_job(self, config: Dict[Text, Any]):
        try:
            k8s_config.load_kube_config(self.kubernetes_config_path)
        except ConfigException as cfg_exc:
            logger.error("The path you provided does not contain a valid"
                         " Kubernetes config.")
            raise
        batch_client = k8s_client.BatchV1Api()
        job_object = self.create_job_object(config)

        namespace = self.namespace or 'default'

        api_response = batch_client.create_namespaced_job(
            body=job_object,
            namespace=namespace)
        logger.info(
            f'Created k8s {api_response.kind} '
            f'({api_response.api_version}): '
            f'{api_response.metadata.name}')

        return None

    def run(self, config: Dict[Text, Any]):
        # Extract the paths to create the tar
        logger.info('Orchestrating pipeline on Kubernetes..')

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
        self.launch_job(config)
