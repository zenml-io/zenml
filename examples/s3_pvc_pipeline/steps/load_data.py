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
"""Load data step: download from S3 and extract into PVC (raw train/test dirs).

Expects S3 layout: s3://{bucket}/{prefix}/{data_version}/train.zip, test.zip
"""

import zipfile
from pathlib import Path
from typing import Annotated, Any, Dict

from zenml import step
from zenml.client import Client


def _download_and_extract_zip(
    s3_client: Any,
    s3_bucket: str,
    s3_key: str,
    dest_dir: Path,
    skip_if_exists: bool = True,
) -> None:
    """Download an S3 zip and extract into dest_dir."""
    if skip_if_exists and (dest_dir / Path(s3_key).name).exists():
        print(
            f"Skipping download and extraction of {s3_key} because it already exists"
        )
        return

    print(f"Downloading s3://{s3_bucket}/{s3_key} to {dest_dir} ...")
    dest_dir.mkdir(parents=True, exist_ok=True)
    buf = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)["Body"].read()
    zip_path = dest_dir / Path(s3_key).name
    zip_path.write_bytes(buf)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)
    zip_path.unlink()


@step
def load_data(
    service_connector_name_or_id: str,
    mount_path: str = "/mnt/data",
    s3_bucket: str = "persistent-data-store",
    s3_prefix: str = "mnist/",
    data_version: str = "v1",
) -> Annotated[Dict[str, str], "raw_data_paths"]:
    """Download versioned data from S3 and extract into PVC (raw train and test dirs).

    If raw train dir already exists and contains .npy files, skips download (cache).

    Args:
        service_connector_name_or_id: ZenML service connector for S3.
        mount_path: Base path where PVC is mounted (e.g. /mnt/data).
        s3_bucket: S3 bucket name.
        s3_prefix: S3 prefix (e.g. mnist/). Combined with data_version for keys.
        data_version: Version key (e.g. v1). Defines PVC subdir and S3 subprefix.

    Returns:
        Dict with "raw_train" and "raw_test" paths on PVC.
    """
    root_dir = Path(mount_path) / data_version
    raw_train_dir = root_dir / "train"
    raw_test_dir = root_dir / "test"

    # Cache: if raw train already has .npy files, skip download
    if raw_train_dir.exists() and raw_test_dir.exists():
        npy_count = sum(1 for _ in raw_train_dir.rglob("*.npy")) + sum(
            1 for _ in raw_test_dir.rglob("*.npy")
        )
        if npy_count > 0:
            print(
                f"\nUsing cached raw data for {data_version=} ({npy_count} .npy files)"
            )
            return {
                "raw_train": str(raw_train_dir),
                "raw_test": str(raw_test_dir),
            }

    print(f"\nLoading data from S3 for {data_version=}")
    s3_client = (
        Client()
        .get_service_connector_client(
            service_connector_name_or_id,
            resource_type="s3-bucket",
            resource_id=f"s3://{s3_bucket}",
        )
        .connect()
    )

    for name, dest in (("train", raw_train_dir), ("test", raw_test_dir)):
        s3_key = f"{s3_prefix.rstrip('/')}/{data_version}/{name}.zip"
        _download_and_extract_zip(
            s3_client=s3_client,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            dest_dir=dest,
            skip_if_exists=True,
        )

    print("Load data done.")
    return {"raw_train": str(raw_train_dir), "raw_test": str(raw_test_dir)}
