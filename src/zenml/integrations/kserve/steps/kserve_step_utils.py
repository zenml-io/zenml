#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Utility functions used by the KServe deployer step."""
import os
import re
import tempfile
from typing import List, Optional

from model_archiver.model_packaging import package_model
from model_archiver.model_packaging_utils import ModelExportUtils
from pydantic import BaseModel

from zenml.exceptions import ValidationError
from zenml.integrations.kserve.services.kserve_deployment import (
    KServeDeploymentConfig,
)
from zenml.integrations.kserve.steps.kserve_deployer import (
    KServeDeployerStepParameters,
)
from zenml.io import fileio
from zenml.utils import io_utils


def is_valid_model_name(model_name: str) -> bool:
    """Checks if the model name is valid.

    Args:
        model_name: the model name to check

    Returns:
        True if the model name is valid, False otherwise.
    """
    pattern = re.compile("^[a-z0-9-]+$")
    return pattern.match(model_name) is not None


def prepare_service_config(
    model_uri: str,
    output_artifact_uri: str,
    params: KServeDeployerStepParameters,
) -> KServeDeploymentConfig:
    """Prepare the model files for model serving.

    This function ensures that the model files are in the correct format
    and file structure required by the KServe server implementation
    used for model serving.

    Args:
        model_uri: the URI of the model artifact being served
        output_artifact_uri: the URI of the output artifact
        params: the KServe deployer step parameters

    Returns:
        The URL to the model is ready for serving.

    Raises:
        RuntimeError: if the model files cannot be prepared.
        ValidationError: if the model name is invalid.
    """
    served_model_uri = os.path.join(output_artifact_uri, "kserve")
    fileio.makedirs(served_model_uri)

    # TODO [ENG-773]: determine how to formalize how models are organized into
    #   folders and sub-folders depending on the model type/format and the
    #   KServe protocol used to serve the model.

    # TODO [ENG-791]: an auto-detect built-in KServe server implementation
    #   from the model artifact type

    # TODO [ENG-792]: validate the model artifact type against the
    #   supported built-in KServe server implementations
    if params.service_config.predictor == "tensorflow":
        # the TensorFlow server expects model artifacts to be
        # stored in numbered subdirectories, each representing a model
        # version
        served_model_uri = os.path.join(
            served_model_uri,
            params.service_config.predictor,
            params.service_config.model_name,
        )
        fileio.makedirs(served_model_uri)
        io_utils.copy_dir(model_uri, os.path.join(served_model_uri, "1"))
    elif params.service_config.predictor == "sklearn":
        # the sklearn server expects model artifacts to be
        # stored in a file called model.joblib
        model_uri = os.path.join(model_uri, "model")
        if not fileio.exists(model_uri):
            raise RuntimeError(
                f"Expected sklearn model artifact was not found at "
                f"{model_uri}"
            )
        served_model_uri = os.path.join(
            served_model_uri,
            params.service_config.predictor,
            params.service_config.model_name,
        )
        fileio.makedirs(served_model_uri)
        fileio.copy(model_uri, os.path.join(served_model_uri, "model.joblib"))
    elif not is_valid_model_name(params.service_config.model_name):
        raise ValidationError(
            f"Model name '{params.service_config.model_name}' is invalid. "
            f"The model name can only include lowercase alphanumeric "
            "characters and hyphens. Please rename your model and try again."
        )
    else:
        # default treatment for all other server implementations is to
        # simply reuse the model from the artifact store path where it
        # is originally stored
        served_model_uri = os.path.join(
            served_model_uri,
            params.service_config.predictor,
            params.service_config.model_name,
        )
        fileio.makedirs(served_model_uri)
        fileio.copy(model_uri, served_model_uri)

    service_config = params.service_config.copy()
    service_config.model_uri = served_model_uri
    return service_config


def prepare_torch_service_config(
    model_uri: str,
    output_artifact_uri: str,
    params: KServeDeployerStepParameters,
) -> KServeDeploymentConfig:
    """Prepare the PyTorch model files for model serving.

    This function ensures that the model files are in the correct format
    and file structure required by the KServe server implementation
    used for model serving.

    Args:
        model_uri: the URI of the model artifact being served
        output_artifact_uri: the URI of the output artifact
        params: the KServe deployer step parameters

    Returns:
        The URL to the model is ready for serving.

    Raises:
        RuntimeError: if the model files cannot be prepared.
    """
    deployment_folder_uri = os.path.join(output_artifact_uri, "kserve")
    served_model_uri = os.path.join(deployment_folder_uri, "model-store")
    config_properties_uri = os.path.join(deployment_folder_uri, "config")
    fileio.makedirs(served_model_uri)
    fileio.makedirs(config_properties_uri)

    if params.torch_serve_parameters is None:
        raise RuntimeError("No torch serve parameters provided")
    else:
        # Create a temporary folder
        temp_dir = tempfile.mkdtemp(prefix="zenml-pytorch-temp-")
        tmp_model_uri = os.path.join(
            str(temp_dir), f"{params.service_config.model_name}.pt"
        )

        # Copy from artifact store to temporary file
        fileio.copy(f"{model_uri}/checkpoint.pt", tmp_model_uri)

        torch_archiver_args = TorchModelArchiver(
            model_name=params.service_config.model_name,
            serialized_file=tmp_model_uri,
            model_file=params.torch_serve_parameters.model_class,
            handler=params.torch_serve_parameters.handler,
            export_path=temp_dir,
            version=params.torch_serve_parameters.model_version,
        )

        manifest = ModelExportUtils.generate_manifest_json(torch_archiver_args)
        package_model(torch_archiver_args, manifest=manifest)

        # Copy from temporary file to artifact store
        archived_model_uri = os.path.join(
            temp_dir, f"{params.service_config.model_name}.mar"
        )
        if not fileio.exists(archived_model_uri):
            raise RuntimeError(
                f"Expected torch archived model artifact was not found at "
                f"{archived_model_uri}"
            )

        # Copy the torch model archive artifact to the model store
        fileio.copy(
            archived_model_uri,
            os.path.join(
                served_model_uri, f"{params.service_config.model_name}.mar"
            ),
        )

        # Get or Generate the config file
        if params.torch_serve_parameters.torch_config:
            # Copy the torch model config to the model store
            fileio.copy(
                params.torch_serve_parameters.torch_config,
                os.path.join(config_properties_uri, "config.properties"),
            )
        else:
            # Generate the config file
            config_file_uri = generate_model_deployer_config(
                model_name=params.service_config.model_name,
                directory=temp_dir,
            )
            # Copy the torch model config to the model store
            fileio.copy(
                config_file_uri,
                os.path.join(config_properties_uri, "config.properties"),
            )

    service_config = params.service_config.copy()
    service_config.model_uri = deployment_folder_uri
    return service_config


class TorchModelArchiver(BaseModel):
    """Model Archiver for PyTorch models.

    Attributes:
        model_name: Model name.
        model_version: Model version.
        serialized_file: Serialized model file.
        handler: TorchServe's handler file to handle custom TorchServe inference logic.
        extra_files: Comma separated path to extra dependency files.
        requirements_file: Path to requirements file.
        export_path: Path to export model.
        runtime: Runtime of the model.
        force: Force export of the model.
        archive_format: Archive format.
    """

    model_name: str
    serialized_file: str
    model_file: str
    handler: str
    export_path: str
    extra_files: Optional[List[str]] = None
    version: Optional[str] = None
    requirements_file: Optional[str] = None
    runtime: Optional[str] = "python"
    force: Optional[bool] = None
    archive_format: Optional[str] = "default"


def generate_model_deployer_config(
    model_name: str,
    directory: str,
) -> str:
    """Generate a model deployer config.

    Args:
        model_name: the name of the model
        directory: the directory where the model is stored

    Returns:
        None
    """
    config_lines = [
        "inference_address=http://0.0.0.0:8085",
        "management_address=http://0.0.0.0:8085",
        "metrics_address=http://0.0.0.0:8082",
        "grpc_inference_port=7070",
        "grpc_management_port=7071",
        "enable_metrics_api=true",
        "metrics_format=prometheus",
        "number_of_netty_threads=4",
        "job_queue_size=10",
        "enable_envvars_config=true",
        "install_py_dep_per_model=true",
        "model_store=/mnt/models/model-store",
    ]

    with tempfile.NamedTemporaryFile(
        suffix=".properties", mode="w+", dir=directory, delete=False
    ) as f:
        for line in config_lines:
            f.write(line + "\n")
        f.write(
            f'model_snapshot={{"name":"startup.cfg","modelCount":1,"models":{{"{model_name}":{{"1.0":{{"defaultVersion":true,"marName":"{model_name}.mar","minWorkers":1,"maxWorkers":5,"batchSize":1,"maxBatchDelay":10,"responseTimeout":120}}}}}}}}'
        )
    f.close()
    return f.name
