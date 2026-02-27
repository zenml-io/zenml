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
"""Preprocess step: train/val split, normalize, write to preprocessed/train, val, test.

Reads raw data (output of load_data step). Expects S3 layout used by load_data.
"""

from pathlib import Path
from typing import Annotated, Dict, List

import numpy as np
from sklearn.model_selection import train_test_split

from zenml import log_metadata, step


def _label_from_path(path: Path) -> int:
    """Class index from path segment 'class_<N>'."""
    for part in path.parts:
        if part.startswith("class_"):
            return int(part.split("_", 1)[1])
    raise ValueError(f"No class_* segment in path: {path}")


def _train_val_split(
    train_dir: Path, train_ratio: float, seed: int
) -> Dict[str, List[Path]]:
    """Return file paths for train/val. Train/val split is stratified by label."""
    train_files = sorted(train_dir.rglob("*.npy"))
    labels = [_label_from_path(p) for p in train_files]
    train_files, val_files = train_test_split(
        train_files,
        train_size=train_ratio,
        stratify=labels,
        random_state=seed,
        shuffle=True,
    )
    return {"train": train_files, "val": val_files}


def _normalize_save(src_fpath: Path, dst_fpath: Path) -> None:
    """Load .npy -> normalize (mean 0.5, std 0.5) -> save."""
    arr = np.load(src_fpath).astype(np.float32) / 255.0
    arr = (arr - 0.5) / 0.5
    dst_fpath.parent.mkdir(parents=True, exist_ok=True)
    np.save(dst_fpath, arr)


@step
def preprocess(
    raw_data_paths: Dict[str, str],
    train_ratio: float,
    seed: int,
    data_version: str,
) -> Annotated[Dict[str, str], "preprocessed_paths"]:
    """Split raw data into train/val/test, normalize, and write to preprocessed dirs.

    Reads from raw_data_paths (output of load_data). Writes to {raw_train.parent}/preprocessed/{train,val,test}.

    Args:
        raw_data_paths: Dict with "raw_train" and "raw_test" from load_data step.
        train_ratio: Fraction of train data for training split; rest for validation.
        seed: Random seed for reproducible train/val split.
        data_version: Version key (for logging).

    Returns:
        Dict with keys "train", "val", "test" mapping to preprocessed directory paths on PVC.
    """
    raw_train_dir = Path(raw_data_paths["raw_train"])
    raw_test_dir = Path(raw_data_paths["raw_test"])
    preprocessed_dir = raw_train_dir.parent / "preprocessed"

    print(f"\nPreprocessing (train/val split + normalize) for {data_version=}")
    train_val_fpaths = _train_val_split(
        train_dir=raw_train_dir, train_ratio=train_ratio, seed=seed
    )
    train_val_test_fpaths = {
        "train": train_val_fpaths["train"],
        "val": train_val_fpaths["val"],
        "test": sorted(raw_test_dir.rglob("*.npy")),
    }

    for split in ("train", "val", "test"):
        src_base = raw_train_dir if split in ("train", "val") else raw_test_dir
        out_base = preprocessed_dir / split
        for src_fpath in train_val_test_fpaths[split]:
            rel_fpath = src_fpath.relative_to(src_base)
            _normalize_save(
                src_fpath=src_fpath, dst_fpath=out_base / rel_fpath
            )
        print(
            f"   {split}: {len(train_val_test_fpaths[split])} files written -> {out_base}/..."
        )

    log_metadata(
        metadata={
            "data_version": data_version,
            "n_train": len(train_val_test_fpaths["train"]),
            "n_val": len(train_val_test_fpaths["val"]),
            "n_test": len(train_val_test_fpaths["test"]),
        },
    )

    print("Preprocessing done.")
    return {
        "train": (preprocessed_dir / "train").as_posix(),
        "val": (preprocessed_dir / "val").as_posix(),
        "test": (preprocessed_dir / "test").as_posix(),
    }
