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
"""Utility functions for the Label Studio annotator integration."""

import os
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote, urlparse

from zenml.io import fileio


def parse_azure_url(url: str) -> Tuple[str, str]:
    """Converts Azure Label Studio URL to path for fileio.

    Args:
        url: Azure Label Studio URL.

    Returns:
        Tuple of (full URL, filename).
    """
    pth = urlparse(url).path
    return f"az://{pth}", pth.split("/")[-1]


def download_azure_image(url: str, destination: str) -> None:
    """Downloads an image using fileio.

    Args:
        url: URL of the image to download.
        destination: Path to the destination file.
    """
    full_url, filename = parse_azure_url(url)
    destination_path = os.path.join(destination, filename)
    fileio.copy(full_url, destination_path)


# def get_azure_credentials() -> Tuple[Optional[str], Optional[str]]:
#     """Returns access credentials for Azure from the environment.

#     Returns:
#         Tuple of (account_name, account_key).
#     """
#     account_key = os.environ.get("AZURE_STORAGE_ACCOUNT_KEY")
#     account_name = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
#     return account_name, account_key


def get_gcs_credentials() -> Optional[str]:
    """Returns access credentials for GCS from the environment.

    Returns:
        GCS credentials string.
    """
    return os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")


# def get_s3_credentials() -> Tuple[Optional[str], Optional[str], Optional[str]]:
#     """Returns access credentials for S3 from the environment.

#     Returns:
#         Tuple of (access_key_id, secret_access_key, session_token).
#     """
#     access_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
#     secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
#     session_token = os.environ.get("AWS_SESSION_TOKEN")
#     return access_key_id, secret_access_key, session_token


def convert_pred_filenames_to_task_ids(
    preds: List[Dict[str, Any]],
    tasks: List[Dict[str, Any]],
    filename_reference: str,
    storage_type: str,
) -> List[Dict[str, Any]]:
    """Converts a list of predictions from local file references to task id.

    Args:
        preds: List of predictions.
        tasks: List of tasks.
        filename_reference: Name of the file reference in the predictions.
        storage_type: Storage type of the predictions.

    Returns:
        List of predictions using task ids as reference.
    """
    filename_id_mapping = {
        os.path.basename(urlparse(task["data"][filename_reference]).path): task[
            "id"
        ]
        for task in tasks
    }

    # GCS and S3 URL encodes filenames containing spaces, requiring this
    # separate encoding step
    if storage_type in {"gcs", "s3"}:
        preds = [
            {"filename": quote(pred["filename"]), "result": pred["result"]}
            for pred in preds
        ]

    return [
        {
            "task": int(
                filename_id_mapping[os.path.basename(pred["filename"])]
            ),
            "result": pred["result"],
        }
        for pred in preds
    ]
