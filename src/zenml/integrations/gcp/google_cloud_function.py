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
from tempfile import TemporaryFile

import googleapiclient.discovery
import requests
from googleapiclient.discovery import Resource

from zenml.logger import get_logger

logger = get_logger(__name__)


def get_cloud_functions_api() -> Resource:
    """Gets the cloud functions API resource client.

    Returns:
        Cloud Functions V2 Resource.
    """
    service = googleapiclient.discovery.build("cloudfunctions", "v2")
    cloud_functions_api = service.projects().locations().functions()
    return cloud_functions_api


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


def upload_directory(parent: str, directory_path: str) -> dict:
    """Creates an upload URL from a provided parent.

    Args:
        parent: Path that looks like projects/{PROJECT}/locations/{REGION}.
        directory_path: Local path of directory to upload.

    Returns:
        Storage source as dict (https://cloud.google.com/functions/docs/reference/rest/v2/projects.locations.functions#StorageSource).
    """
    upload_url = (
        get_cloud_functions_api()
        .generateUploadUrl(parent=parent, body={})
        .execute()["uploadUrl"]
    )
    logger.debug("Create Upload URL", upload_url)

    with TemporaryFile() as data:
        with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as archive:
            zipdir(directory_path, archive)
        data.seek(0)
        headers = {
            "content-type": "application/zip",
            "x-goog-content-length-range": "0,104857600",
        }
        res = requests.put(upload_url, headers=headers, data=data)
    logger.debug(f"Uploaded function directory. Response: {res}")
    return res["storageSource"]


def create_cloud_function(
    directory_path: str,
    project: str,
    location: str,
    function_name: str,
) -> str:
    """Create google cloud function from specified directory path.

    Args:
        directory_path: Local path to directory where function code resides.
        project: GCP project ID.
        location: GCP location name.
        function_name: Name of the function to create.
        timeout: Timeout seconds while creaing functions. Defaults to 200 seconds.

    Returns:
        str: URI of the created cloud function.
    """
    parent = "projects/{}/locations/{}".format(project, location)

    storage_source = upload_directory(parent, directory_path)
    config = {
        "name": parent + "/functions/" + function_name,
        "buildConfig": {
            "entryPoint": "trigger_vertex_job",
            "runtime": "python37",
            "availableMemoryMb": 128,
            "source": {"storageSource": storage_source},
        },
    }

    logger.debug(f"Creating function with config: {config}")
    res = (
        get_cloud_functions_api().create(location=parent, body=config).execute()
    )
    logger.debug(f"Function {function_name} created. Response: {res}")
    return f"https://{location}-{project}.cloudfunctions.net/{function_name}"
