#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
from kubernetes import client as k8s_client


def create_seldon_core_custom_spec(
    model_uri: str,
    custom_docker_image: str,
    secret_name: str,
) -> k8s_client.V1PodSpec:
    """Create a custom pod spec for the seldon core container.

    Returns:
        A pod spec for the seldon core container.
    """
    volume = k8s_client.V1Volume(
        name="classifier-provision-location",
        empty_dir=k8s_client.V1EmptyDirVolumeSource(),
    )
    init_container = k8s_client.V1Container(
        name="classifier-model-initializer",
        image="seldonio/rclone-storage-initializer:1.14.0-dev",
        image_pull_policy="IfNotPresent",
        args=[model_uri, "/mnt/models"],
        volume_mounts=[
            k8s_client.V1VolumeMount(
                name="classifier-provision-location", mount_path="/mnt/models"
            )
        ],
        env_from=[
            k8s_client.V1EnvFromSource(
                secret_ref=k8s_client.V1SecretEnvSource(name=secret_name)
            )
        ],
    )
    image_pull_secret = k8s_client.V1LocalObjectReference(name=secret_name)

    container = k8s_client.V1Container(
        name="classifier",
        image=custom_docker_image,
        image_pull_policy="IfNotPresent",
        volume_mounts=[
            k8s_client.V1VolumeMount(
                name="classifier-provision-location",
                mount_path="/mnt/models",
                read_only=True,
            )
        ],
        env=[
            k8s_client.V1EnvVar(
                name="PREDICTIVE_UNIT_PARAMETERS",
                value='[{"name":"model_uri","value":"/mnt/models","type":"STRING"}]',
            )
        ],
    )
    return k8s_client.V1PodSpec(
        volumes=[
            volume,
        ],
        image_pull_secrets=[image_pull_secret],
        init_containers=[
            init_container,
        ],
        containers=[container],
    )
