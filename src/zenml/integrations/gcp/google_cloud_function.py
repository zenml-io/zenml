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
import zipfile
from typing import TYPE_CHECKING, Optional

import requests
from google.cloud import functions_v2
from google.cloud.functions_v2.types import (
    BuildConfig,
    CreateFunctionRequest,
    Function,
    Source,
)

from zenml.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from google.auth.credentials import Credentials


def get_cloud_functions_api(
    credentials: Optional["Credentials"] = None,
) -> functions_v2.FunctionServiceClient:
    """Gets the cloud functions API resource client.

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
    parent: str,
    directory_path: str,
    credentials: Optional["Credentials"] = None,
) -> dict:
    """Creates an upload URL from a provided parent.

    Args:
        parent: Path that looks like projects/{PROJECT}/locations/{REGION}.
        directory_path: Local path of directory to upload.
        credentials: Credentials to use for GCP services.

    Returns:
        Storage source as dict (https://cloud.google.com/functions/docs/reference/rest/v2/projects.locations.functions#StorageSource).
    """
    request = functions_v2.GenerateUploadUrlRequest(
        parent=parent,
    )
    response = get_cloud_functions_api(
        credentials=credentials
    ).generate_upload_url(request=request)
    logger.debug(f"Create Upload URL response: {response}")

    upload_url = response.upload_url

    with open("temp.zip", "wb") as data:
        with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as archive:
            zipdir(directory_path, archive)
        data.seek(0)

    headers = {
        "content-type": "application/zip",
        "x-goog-content-length-range": "0,104857600",
    }
    with open("temp.zip", "rb") as data:
        res = requests.post(upload_url, headers=headers, data=data)
    logger.debug(f"Uploaded function directory. Response: {res.text}")

    from zenml.io import fileio

    fileio.copy("temp.zip", "gs://ing-store/temp.zip", overwrite=True)
    response.storage_source.bucket = "ing-store"
    response.storage_source.object_ = "temp.zip"

    return response.storage_source


def create_cloud_function(
    directory_path: str,
    project: str,
    location: str,
    function_name: str,
    credentials: Optional["Credentials"] = None,
) -> str:
    """Create google cloud function from specified directory path.

    Args:
        directory_path: Local path to directory where function code resides.
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

    storage_source = upload_directory(
        parent, directory_path, credentials=credentials
    )

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

    # response = operation.result()

    return f"https://{location}-{project}.cloudfunctions.net/{function_name}"
