#!/usr/bin/env python3
"""Download FashionMNIST and upload to S3 as zipped archives.

Uploads:
  s3://{bucket}/mnist/{version}/train.zip
  s3://{bucket}/mnist/{version}/test.zip

Each zip contains: class_{label}/{index:05d}.npy (28x28 uint8).

# train.zip:
train/
├── class_0/
│   ├── 00000.npy
│   ├── 00001.npy
│   └── ...
├── class_1/
│   ├── 00000.npy
│   ├── 00001.npy
│   └── ...
...
├── class_9/
│   ├── 00000.npy
│   ├── 00001.npy
│   └── ...


# test.zip:
test/
├── class_0/
├── class_1/
...
├── class_9/

Usage:

    # Upload to S3
    AWS_PROFILE=zenml-dev uv run scripts/upload_mnist_to_s3.py

    # Only download + prepare locally (no upload)
    uv run scripts/upload_mnist_to_s3.py --dry-run
"""

import argparse
import tempfile
import zipfile
from pathlib import Path

import numpy as np
from torchvision import datasets, transforms

THiS_DIR = Path(__file__).resolve().parent
DATA_DIR = THiS_DIR / "../data"

S3_BUCKET = "persistent-data-store"
DATA_VERSION = "v1"
S3_DATA_PREFIX = f"mnist/{DATA_VERSION}"


def write_split(dataset: datasets.FashionMNIST, out_dir: Path) -> None:
    """Write dataset into out_dir/class_{label}/{k:05d}.npy with per-class counters."""
    counters: dict[int, int] = {}
    out_dir.mkdir(parents=True, exist_ok=True)

    for img, label in dataset:
        label = int(label)
        k = counters.get(label, 0)
        counters[label] = k + 1

        class_dir = out_dir / f"class_{label}"
        class_dir.mkdir(parents=True, exist_ok=True)

        # img is a torch Tensor (1,28,28) float in [0,1]; convert to uint8 (28,28)
        arr = img.mul(255).byte().squeeze(0).numpy()
        np.save(class_dir / f"{k:05d}.npy", arr)

    print(f"Wrote {len(dataset)} images to {out_dir}")


def zip_dir(src_dir: Path, zip_path: Path) -> int:
    """Zip all .npy files in src_dir to zip_path. Returns size in bytes."""
    with zipfile.ZipFile(
        zip_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as zf:
        for p in src_dir.rglob("*.npy"):
            zf.write(p, arcname=p.relative_to(src_dir))
    return zip_path.stat().st_size


def upload_file_to_s3(zip_path: Path, bucket: str, key: str) -> None:
    import boto3  # keep optional unless uploading

    s3 = boto3.client("s3")
    s3.upload_file(
        str(zip_path),
        bucket,
        key,
        ExtraArgs={"ContentType": "application/zip"},
    )


def zip_and_upload_to_s3(
    src_dir: Path, bucket: str, key: str, dry_run: bool
) -> None:
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        zip_path = Path(tmp.name)

    try:
        size = zip_dir(src_dir, zip_path)
        size_mb = size / (1024 * 1024)
        print(f"   Built {src_dir.name}.zip ({size_mb:.2f} MB)")

        if dry_run:
            print(f"   Dry run: would upload to s3://{bucket}/{key}")
            return

        print(f"   Uploading to s3://{bucket}/{key} ...")
        upload_file_to_s3(zip_path, bucket, key)
    finally:
        zip_path.unlink(missing_ok=True)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Upload FashionMNIST to S3 as class-sharded .npy zips."
    )
    ap.add_argument("--dry-run", action="store_true", help="Dry run")
    args = ap.parse_args()

    print("Downloading FashionMNIST...")
    tfm = transforms.ToTensor()  # ensures consistent tensor format
    train = datasets.FashionMNIST(
        root=str(DATA_DIR),
        train=True,
        download=True,
        transform=tfm,
    )
    test = datasets.FashionMNIST(
        root=str(DATA_DIR),
        train=False,
        download=True,
        transform=tfm,
    )
    print(f"Train: {len(train)}  Test: {len(test)}")

    print("Saving data by class...")
    out_base_dir = DATA_DIR / S3_DATA_PREFIX

    write_split(dataset=train, out_dir=out_base_dir / "train")
    write_split(dataset=test, out_dir=out_base_dir / "test")

    print("Zipping + uploading...")
    for dataset_type in ("train", "test"):
        zip_and_upload_to_s3(
            src_dir=out_base_dir / dataset_type,
            bucket=S3_BUCKET,
            key=f"{S3_DATA_PREFIX}/{dataset_type}.zip",
            dry_run=args.dry_run,
        )
    print("Done.")


if __name__ == "__main__":
    main()
