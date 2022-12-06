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
"""Utils for the Google Cloud Functions API."""

import os
import tempfile
import time
import zipfile
from typing import TYPE_CHECKING, Optional

from google.cloud import functions_v2
from google.cloud.functions_v2.types import (
    BuildConfig,
    CreateFunctionRequest,
    Function,
    GetFunctionRequest,
    Source,
    StorageSource,
)

from zenml.io import fileio
from zenml.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from google.auth.credentials import Credentials


def get_cloud_functions_api(
    credentials: Optional["Credentials"] = None,
) -> functions_v2.FunctionServiceClient:
    """Gets the cloud functions API resource client.

    Args:
        credentials: Google cloud credentials.

    Returns:
        Cloud Functions V2 Client.
    """
    return functions_v2.FunctionServiceClient(credentials=credentials)


def zipdir(path: str, ziph: zipfile.ZipFile) -> None:
    """Zips a directory using an Zipfile object.

    Args:
        path: Path to zip directory to.
        ziph: A `zipfile.Zipfile` file object.
    """
    for root, _, files in os.walk(path):
        for file in files:
            if file != "__init__.py":
                ziph.write(os.path.join(root, file), file)


def upload_directory(
    directory_path: str,
    upload_path: str,
) -> dict:
    """Uploads local directory to remote one.

    Args:
        upload_path: GCS path where to upload the zipped function code.
        directory_path: Local path of directory to upload.

    Returns:
        Storage source (https://cloud.google.com/functions/docs/reference/rest/v2/projects.locations.functions#StorageSource).
    """
    with tempfile.NamedTemporaryFile(delete=False) as f:
        with open(f.name, "wb") as data:
            with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as archive:
                zipdir(directory_path, archive)
            data.seek(0)

    # Copy and remove
    fileio.copy(f.name, upload_path, overwrite=True)
    fileio.remove(f.name)

    # Split the path by "/" character
    parts = upload_path.replace("gs://", "").split("/")

    # The first part will be the bucket, and the rest will be the object path
    bucket = parts[0]
    object_path = "/".join(parts[1:])

    return StorageSource(
        bucket=bucket,
        object_=object_path,
    )


def create_cloud_function(
    directory_path: str,
    upload_path: str,
    project: str,
    location: str,
    function_name: str,
    credentials: Optional["Credentials"] = None,
) -> str:
    """Create google cloud function from specified directory path.

    Args:
        directory_path: Local path to directory where function code resides.
        upload_path: GCS path where to upload the function code.
        project: GCP project ID.
        location: GCP location name.
        function_name: Name of the function to create.
        credentials: Credentials to use for GCP services.

    Returns:
        str: URI of the created cloud function.
    """
    sanitized_function_name = function_name.replace("_", "-")

    parent = "projects/{}/locations/{}".format(project, location)
    logger.info(
        f"Creating Google Cloud Function: {parent}/functions/{function_name}"
    )

    storage_source = upload_directory(directory_path, upload_path)

    # Make the request
    operation = get_cloud_functions_api(
        credentials=credentials
    ).create_function(
        #  parent=parent + "/functions/" + function_name,
        request=CreateFunctionRequest(
            parent=parent,
            function_id=sanitized_function_name,
            function=Function(
                name=parent + "/functions/" + sanitized_function_name,
                # environment=Environment(value=2),
                build_config=BuildConfig(
                    entry_point="trigger_vertex_job",
                    runtime="python38",
                    source=Source(storage_source=storage_source),
                ),
            ),
        )
    )

    state = Function.State.DEPLOYING
    logger.info(
        "Creating function... This might take a few minutes. "
        "Please do not exit the program at this point..."
    )
    while state == Function.State.DEPLOYING:
        response = get_cloud_functions_api(
            credentials=credentials
        ).get_function(
            request=GetFunctionRequest(
                name=parent + "/functions/" + sanitized_function_name
            )
        )
        state = response.state
        logger.info("Still creating... sleeping for 5 seconds...")
        time.sleep(5)

    logger.info(f"Done! Function available at {response.service_config.uri}")
    return response.service_config.uri
