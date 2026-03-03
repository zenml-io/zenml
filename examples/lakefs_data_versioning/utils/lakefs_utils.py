#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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

"""Helpers for interacting with LakeFS via its SDK and S3-compatible gateway.

All data reads/writes go through the S3 gateway (boto3) so the same code
works against real S3 with minimal changes. The LakeFS SDK is used only
for repository management, branching, and commits.
"""

import io
import os
from typing import Any

import boto3
import lakefs_sdk
import pandas as pd
from lakefs_sdk.client import LakeFSClient
from lakefs_sdk.exceptions import ApiException

from zenml.logger import get_logger

logger = get_logger(__name__)

LAKEFS_ENDPOINT = os.environ.get("LAKEFS_ENDPOINT", "http://localhost:8000")
LAKEFS_ACCESS_KEY = os.environ.get("LAKEFS_ACCESS_KEY_ID", "AKIAIOSFOLAKEFS")
LAKEFS_SECRET_KEY = os.environ.get(
    "LAKEFS_SECRET_ACCESS_KEY",
    "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
)
LAKEFS_STORAGE_NAMESPACE = os.environ.get(
    "LAKEFS_STORAGE_NAMESPACE", "local://data"
)


def get_lakefs_client() -> LakeFSClient:
    """Return a configured LakeFS SDK client."""
    config = lakefs_sdk.Configuration(
        host=f"{LAKEFS_ENDPOINT}/api/v1",
        username=LAKEFS_ACCESS_KEY,
        password=LAKEFS_SECRET_KEY,
    )
    return LakeFSClient(config)


def get_s3_client() -> Any:
    """Return a boto3 S3 client pointed at the LakeFS S3 gateway.

    LakeFS exposes an S3-compatible API on the same port as the main
    service. Bucket names map to LakeFS repository names, and object
    keys are prefixed with the branch or commit ref.
    """
    return boto3.client(
        "s3",
        endpoint_url=LAKEFS_ENDPOINT,
        aws_access_key_id=LAKEFS_ACCESS_KEY,
        aws_secret_access_key=LAKEFS_SECRET_KEY,
    )


def setup_lakefs_repo(repo_name: str) -> None:
    """Create the LakeFS repository if it does not already exist."""
    client = get_lakefs_client()
    try:
        client.repositories_api.get_repository(repo_name)
        logger.info("LakeFS repository '%s' already exists.", repo_name)
    except ApiException as e:
        if e.status == 404:
            client.repositories_api.create_repository(
                lakefs_sdk.RepositoryCreation(
                    name=repo_name,
                    storage_namespace=(
                        f"{LAKEFS_STORAGE_NAMESPACE}/{repo_name}"
                    ),
                    default_branch="main",
                )
            )
            logger.info("Created LakeFS repository '%s'.", repo_name)
        else:
            raise


def create_branch(
    repo: str,
    branch_name: str,
    source_branch: str = "main",
) -> None:
    """Create a new branch in LakeFS off the given source branch."""
    client = get_lakefs_client()
    client.branches_api.create_branch(
        repository=repo,
        branch_creation=lakefs_sdk.BranchCreation(
            name=branch_name,
            source=source_branch,
        ),
    )
    logger.info(
        "Created branch '%s' from '%s' in repo '%s'.",
        branch_name,
        source_branch,
        repo,
    )


def commit_branch(repo: str, branch: str, message: str) -> str:
    """Commit the current state of a LakeFS branch.

    Returns:
        The commit SHA (hex string).
    """
    client = get_lakefs_client()
    commit = client.commits_api.commit(
        repository=repo,
        branch=branch,
        commit_creation=lakefs_sdk.CommitCreation(message=message),
    )
    logger.info(
        "Committed branch '%s' in repo '%s': %s",
        branch,
        repo,
        commit.id,
    )
    return commit.id


def write_parquet_to_lakefs(
    df: pd.DataFrame,
    repo: str,
    branch: str,
    path: str,
) -> None:
    """Write a DataFrame as Parquet to LakeFS via the S3 gateway.

    Args:
        df: Data to write.
        repo: LakeFS repository name (used as the S3 bucket).
        branch: Branch name (prefixed to the object key).
        path: Object path within the branch (e.g. "raw/data.parquet").
    """
    s3 = get_s3_client()
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False)
    buffer.seek(0)

    key = f"{branch}/{path}"
    s3.upload_fileobj(buffer, repo, key)
    logger.info(
        "Wrote %d rows to s3://%s/%s",
        len(df),
        repo,
        key,
    )


def read_parquet_from_lakefs(
    repo: str,
    ref: str,
    path: str,
) -> pd.DataFrame:
    """Read a Parquet file from LakeFS via the S3 gateway.

    Args:
        repo: LakeFS repository name (S3 bucket).
        ref: Branch name or commit SHA.
        path: Object path within the ref.

    Returns:
        The data as a pandas DataFrame.
    """
    s3 = get_s3_client()
    buffer = io.BytesIO()
    key = f"{ref}/{path}"
    s3.download_fileobj(repo, key, buffer)
    buffer.seek(0)
    df = pd.read_parquet(buffer)
    logger.info(
        "Read %d rows from s3://%s/%s",
        len(df),
        repo,
        key,
    )
    return df
