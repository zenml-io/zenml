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


def clean_url(url: str) -> str:
    """Remove extraneous parts of the URL prior to mapping.

    Removes the query and netloc parts of the URL, and strips the leading slash
    from the path. For example, a string like
    `'gs%3A//label-studio/load_image_data/images/fdbcd451-0c80-495c-a9c5-6b51776f5019/1/0/image_file.JPEG'`
    would become
    `label-studio/load_image_data/images/fdbcd451-0c80-495c-a9c5-6b51776f5019/1/0/image_file.JPEG`.

    Args:
        url: A URL string.

    Returns:
        A cleaned URL string.
    """
    parsed = urlparse(url)
    parsed = parsed._replace(netloc="", query="")
    return parsed.path.lstrip("/")


def convert_pred_filenames_to_task_ids(
    preds: List[Dict[str, Any]],
    tasks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Converts a list of predictions from local file references to task id.

    Args:
        preds: List of predictions.
        tasks: List of tasks.

    Returns:
        List of predictions using task ids as reference.
    """
    preds = [
        {
            "filename": quote(pred["filename"]).split("//")[1],
            "result": pred["result"],
        }
        for pred in preds
    ]
    filename_id_mapping = {
        clean_url(task["storage_filename"]): task["id"] for task in tasks
    }
    return [
        {
            "task": int(
                filename_id_mapping["/".join(pred["filename"].split("/")[1:])]
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
