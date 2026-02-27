# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2026. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Training pipeline: load_data → preprocess → train → test."""

from typing import Any, Dict

from steps import preprocess, test_model
from steps.load_data import load_data
from steps.train_model import train_model

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.integrations.kubernetes.flavors.kubernetes_orchestrator_flavor import (
    KubernetesOrchestratorSettings,
)
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings

# PVC for preprocessed data on Kubernetes (cache for S3 data; not cleaned after run).
PREPROCESS_PVC_CLAIM_NAME = "zenml-data-pvc"
PREPROCESS_MOUNT_PATH = "/mnt/data"

pod_settings = KubernetesPodSettings(
    volumes=[
        {
            "name": "data-volume",
            "persistentVolumeClaim": {"claimName": PREPROCESS_PVC_CLAIM_NAME},
        }
    ],
    volume_mounts=[
        {"name": "data-volume", "mountPath": PREPROCESS_MOUNT_PATH},
    ],
    resources={
        "requests": {"cpu": "2", "memory": "4Gi"},
        "limits": {"cpu": "2", "memory": "4Gi"},
    },
)
k8s_settings = KubernetesOrchestratorSettings(pod_settings=pod_settings)

docker_settings = DockerSettings(requirements="requirements.txt")


@pipeline(
    settings={"orchestrator": k8s_settings, "docker": docker_settings},
    enable_cache=False,
)
def train_pipeline(
    service_connector_name_or_id: str,
    s3_bucket: str,
    s3_prefix: str,
    data_version: str,
    train_ratio: float,
    seed: int,
    hyperparams: Dict[str, Any],
    preprocess_mount_path: str = PREPROCESS_MOUNT_PATH,
) -> None:
    """Load data (S3 → PVC) → preprocess (split + normalize) → train → test.

    Train and test results are printed and logged as metadata in their steps.

    Data is stored under /mnt/data/{data_version}/.

    Args:
        service_connector_name_or_id: ZenML service connector name or ID for S3 Bucket access.
        s3_bucket: S3 bucket name containing the versioned data.
        s3_prefix: S3 key prefix (e.g. mnist/). Version is appended as {prefix}/{data_version}/.
        data_version: Data version key (e.g. v1). Used for PVC paths and S3 prefix.
        train_ratio: Fraction of training data used for train split (rest for val).
        seed: Random seed for reproducibility (train/val split, training, evaluation).
        preprocess_mount_path: PVC mount path for data (e.g. /mnt/data).
        hyperparams: Training hyperparameters (learning_rate, batch_size, hidden_dim, max_epochs).
    """
    raw_data_paths = load_data(
        service_connector_name_or_id=service_connector_name_or_id,
        mount_path=preprocess_mount_path,
        s3_bucket=s3_bucket,
        s3_prefix=s3_prefix,
        data_version=data_version,
    )
    preprocessed_paths = preprocess(
        raw_data_paths=raw_data_paths,
        train_ratio=train_ratio,
        seed=seed,
        data_version=data_version,
    )
    trained_model_path = train_model(
        preprocessed_paths=preprocessed_paths,
        hyperparams=hyperparams,
        seed=seed,
    )

    test_model(
        trained_model_path=trained_model_path,
        preprocessed_paths=preprocessed_paths,
        seed=seed,
    )
