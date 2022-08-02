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
from typing import Any, Dict, List
from urllib.parse import quote, urlparse


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


def is_s3_url(url: str) -> bool:
    """Return whether the given URL is an S3 URL.

    Args:
        url: URL to check.

    Returns:
        True if the URL is an S3 URL, False otherwise.
    """
    return "s3.amazonaws" in urlparse(url).netloc


def is_azure_url(url: str) -> bool:
    """Return whether the given URL is an Azure URL.

    Args:
        url: URL to check.

    Returns:
        True if the URL is an Azure URL, False otherwise.
    """
    return "blob.core.windows.net" in urlparse(url).netloc


def is_gcs_url(url: str) -> bool:
    """Return whether the given URL is an GCS URL.

    Args:
        url: URL to check.

    Returns:
        True if the URL is an GCS URL, False otherwise.
    """
    return "storage.googleapis.com" in urlparse(url).netloc


def get_file_extension(path_str: str) -> str:
    """Return the file extension of the given filename.

    Args:
        path_str: Path to the file.

    Returns:
        File extension.
    """
    return os.path.splitext(urlparse(path_str).path)[1]
