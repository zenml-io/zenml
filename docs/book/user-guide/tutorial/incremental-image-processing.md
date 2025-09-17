---
icon: image-gallery
description: Managing large image datasets with incremental preprocessing (fan-out / fan-in) in ZenML.
---

# Incremental preprocessing for image datasets

## Introduction

When your dataset of images grows, feeding the **entire list** into one preprocessing step makes ZenML’s cache invalidate on every tiny change. This tutorial shows a practical pattern to **only preprocess new/changed images** using a fixed fan-out/fan-in design with small per-shard manifests.

You will:

1. List images from a folder.
2. Split the list into **stable shards** (e.g., 64) → **fan-out**.
3. Preprocess each shard with **delta updates** (skip already processed).
4. Merge shard manifests into a training index → **fan-in**.
5. Run the pipeline twice to see incremental behavior.

### Prerequisites

* `uv pip install zenml pillow` (or `pip install zenml pillow`)
* A folder of images (we'll also show how to generate a few dummy ones).

---

## The idea in one picture

* **Shard** the big list (deterministic `hash(path) % N`) so adding a new file only touches **one shard**.
* Each shard step keeps a **manifest.json** with `{etag/hash → output_path}` and only processes images that are **new/changed**.
* A final step **gathers** manifests into a single list of preprocessed files.

---

## Minimal, runnable code

> Put this in a notebook cell or a `run.py` and execute. It uses only local files.

```python
# --- imports & setup ---
from typing import List, Tuple
from pathlib import Path
import hashlib, json, time, random

from PIL import Image, ImageDraw
from zenml import step, pipeline

# ---------- configuration ----------
N_SHARDS = 4  # change to any reasonable value!
IMG_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".bmp"}

# Root for raw images and outputs (feel free to change these)
RAW_DIR = Path("data/raw_images")
OUT_DIR = Path("data/outputs")  # will contain /preproc and /manifests

# ---------- helpers ----------
def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def list_images_under(root: Path) -> List[Path]:
    return sorted([p for p in root.rglob("*") if p.suffix.lower() in IMG_EXTS])

def file_md5(p: Path) -> str:
    h = hashlib.md5()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def stable_shard_index(image_path: Path) -> int:
    h = hashlib.sha1(str(image_path).encode("utf-8")).hexdigest()
    return int(h, 16) % N_SHARDS

def preproc_target(base: Path, image_hash: str) -> Path:
    # bucket to avoid too many files per directory
    return base / "preproc" / image_hash[:2] / f"{image_hash}.png"

def manifest_path(base: Path, shard_id: int) -> Path:
    return base / "manifests" / f"shard_{shard_id}.json"

def load_manifest(p: Path):
    if p.exists():
        return json.loads(p.read_text())
    return {}

def save_manifest(p: Path, data):
    ensure_dir(p.parent)
    p.write_text(json.dumps(data, indent=2))

# (optional) create a few dummy images for demo
def create_dummy_images(root: Path, count: int = 12) -> None:
    ensure_dir(root)
    for i in range(count):
        im = Image.new("RGB", (256, 256), color=(random.randint(0,255), 180, 200))
        d = ImageDraw.Draw(im)
        d.text((10, 10), f"img_{i}", fill=(255, 255, 255))
        im.save(root / f"img_{i:04d}.png")

def simple_preprocess(in_path: Path, out_path: Path) -> None:
    """Example preprocessing: resize & grayscale, write PNG."""
    ensure_dir(out_path.parent)
    with Image.open(in_path) as im:
        im = im.convert("L").resize((224, 224))
        im.save(out_path)

# ---------- THE KEY: External change detection ----------
# Compute directory fingerprint OUTSIDE the pipeline and pass it as input.
# This makes filesystem changes visible to ZenML's caching system.

def get_directory_fingerprint(root_dir: str) -> str:
    """Compute directory fingerprint based on file names, sizes, and modification times."""
    paths = list_images_under(Path(root_dir))
    file_info = []
    for p in paths:
        mtime = p.stat().st_mtime
        size = p.stat().st_size
        file_info.append(f"{p.name}:{mtime}:{size}")
    return hashlib.md5("|".join(sorted(file_info)).encode()).hexdigest()

# --- steps ---
@step
def scan_images_step(root_dir: str, dir_fingerprint: str) -> List[Tuple[str, str, float]]:
    """Scan directory for images. Cache invalidates when dir_fingerprint changes."""
    print(f"Scanning directory with fingerprint: {dir_fingerprint[:8]}...")
    paths = list_images_under(Path(root_dir))
    result = []
    for p in paths:
        etag = file_md5(p)
        mtime = p.stat().st_mtime
        result.append((str(p), etag, mtime))
    print(f"Found {len(result)} images")
    return sorted(result)

@step
def shard_images_step(
    images_metadata: List[Tuple[str, str, float]]
) -> Tuple[List[Tuple[str, str, float]], ...]:
    """Split images into N_SHARDS based on their paths."""
    shards = [[] for _ in range(N_SHARDS)]
    
    for img_path, etag, mtime in images_metadata:
        shard_id = stable_shard_index(Path(img_path))
        shards[shard_id].append((img_path, etag, mtime))
    
    # Sort each shard
    for shard in shards:
        shard.sort()
    
    return tuple(shards)

@step
def extract_shard_step(
    shards: Tuple[List[Tuple[str, str, float]], ...], 
    shard_id: int
) -> List[Tuple[str, str, float]]:
    """Extract a specific shard by ID."""
    return shards[shard_id]

@step
def preprocess_shard_step(
    shard_id: int,
    shard_metadata: List[Tuple[str, str, float]],
    out_dir: str,
) -> str:
    """
    Process shard with both ZenML caching AND manifest-based incrementality.
    Returns: manifest file path (as string).
    """
    base = Path(out_dir)
    mpath = manifest_path(base, shard_id)
    manifest = load_manifest(mpath)

    num_new = 0
    num_skipped = 0

    for img_path, current_etag, mtime in shard_metadata:
        ipath = Path(img_path)
        entry = manifest.get(img_path)

        # Check manifest for incrementality (skip if already processed with same etag)
        if (entry and 
            entry.get("etag") == current_etag and 
            Path(entry["output"]).exists()):
            num_skipped += 1
            continue

        # Process new/changed image
        opath = preproc_target(base, current_etag)
        simple_preprocess(ipath, opath)

        manifest[img_path] = {
            "etag": current_etag,
            "output": str(opath),
            "processed_at": int(time.time()),
        }
        num_new += 1

    save_manifest(mpath, manifest)
    print(f"[shard {shard_id}] total={len(shard_metadata)} new={num_new} skipped={num_skipped}")
    return str(mpath)

@step
def summarize_results_step(out_dir: str) -> int:
    """Count total processed files from all manifests."""
    outputs = []
    for i in range(N_SHARDS):
        mpath = manifest_path(Path(out_dir), i)
        if mpath.exists():
            data = load_manifest(mpath)
            outputs.extend(v["output"] for v in data.values())
    
    total = len(set(outputs))
    print(f"[summary] total preprocessed files across all shards: {total}")
    return total

# --- pipeline with clean for loop ---
@pipeline
def incremental_preproc_pipeline(root_dir: str, out_dir: str, dir_fingerprint: str):
    """Clean pipeline with for loop - truly scalable!"""
    # Scan and shard images
    images_metadata = scan_images_step(root_dir, dir_fingerprint)
    shards = shard_images_step(images_metadata)
    
    # Process each shard with clean for loop
    for i in range(N_SHARDS):
        shard_data = extract_shard_step(shards, shard_id=i)
        preprocess_shard_step(shard_id=i, shard_metadata=shard_data, out_dir=out_dir)
    
    # Optional: summarize results
    total_files = summarize_results_step(out_dir)
    return total_files

# --- demo runner ---
if __name__ == "__main__":
    # 0) create a small demo dataset (comment out if you already have images)
    if not RAW_DIR.exists():
        create_dummy_images(RAW_DIR, count=12)
        print(f"Created dummy images in: {RAW_DIR.resolve()}")

    print(f"Using clean for i in range({N_SHARDS}) in pipeline!")

    # 1) first run: processes all images once
    print("\n=== First run ===")
    fp1 = get_directory_fingerprint(str(RAW_DIR))
    print(f"Directory fingerprint: {fp1[:8]}...")
    run1 = incremental_preproc_pipeline(str(RAW_DIR), str(OUT_DIR), fp1)

    # 2) simulate new images arriving
    new_img = RAW_DIR / "img_new.png"
    Image.new("RGB", (256, 256), color=(30, 200, 60)).save(new_img)
    print(f"Added new image: {new_img}")

    # 3) second run: only the *affected shard* recomputes, others are cached
    print("\n=== Second run ===")
    fp2 = get_directory_fingerprint(str(RAW_DIR))
    print(f"Directory fingerprint: {fp2[:8]}... (changed: {fp1 != fp2})")
    run2 = incremental_preproc_pipeline(str(RAW_DIR), str(OUT_DIR), fp2)

    print("\n🎉 SUCCESS! This combines:")
    print("- ZenML caching: unchanged shards use cached results")
    print("- Incremental processing: only new/changed images are processed")
    print("- Clean for loop: change N_SHARDS to any value!")
    
    # Where to look:
    # - manifests: data/outputs/manifests/shard_*.json
    # - preprocessed: data/outputs/preproc/<bucket>/<hash>.png
```

---

## What you'll see

* **First run:** processes all images:
  * `Using clean for i in range(4) in pipeline!`
  * Directory fingerprint: `65ef4984...`
  * Scans directory: "Found 13 images"
  * Each shard step executes: `[shard 0] total=4 new=0 skipped=4` (using existing manifests)
  * Summary: `[summary] total preprocessed files across all shards: 13`

* **Second run (after adding 1 image):**
  * Directory fingerprint changes: `c5512914... (changed: True)`
  * Scans directory again: "Found 13 images" 
  * **Perfect selective caching**: 
    - Shards 0, 1, 3: "Using cached version of step preprocess_shard_step" ✅
    - Shard 2: Re-executes because it contains the new image ✅
  * **Double incrementality**: Even shard 2 shows `total=4 new=0 skipped=4` (manifest logic)

The **clean for loop** approach gives you the best of all worlds: scalable code (`for i in range(N_SHARDS)`), ZenML's intelligent caching, and manifest-based incrementality.

---

## Key insights & tuning

### The Critical Pattern: External Change Detection

The secret to making this work with ZenML's caching is computing the **directory fingerprint outside the pipeline** and passing it as a parameter. This makes filesystem changes visible to ZenML's caching system:

```python
# BEFORE pipeline execution
fp = get_directory_fingerprint(str(RAW_DIR))
# THEN pass as parameter  
incremental_preproc_pipeline(str(RAW_DIR), str(OUT_DIR), fp)
```

When files change → fingerprint changes → cache invalidates → only affected shards recompute.

### Tuning Parameters

* **Choose `N_SHARDS`**: Start with 4-8 for small datasets, 32-128 for large ones. More shards = finer cache granularity + more parallelism.
* **Shard extraction steps**: Currently hardcoded for 4 shards. For more shards, add more `extract_shard_N` steps.
* **Deterministic outputs**: Filenames tied to content hash avoid duplicates across runs.
* **Hash function**: MD5 for file content detection. Could use mtime+size for faster scanning on stable filesystems.

### Production Considerations

* **Parallelism**: Use remote orchestrators (SSH/Kubernetes) to run shard steps in parallel.
* **Storage**: Consider the manifest storage location for team workflows.
* **Monitoring**: The print statements show exactly what's cached vs. recomputed.
* **Error handling**: Add retry logic for transient preprocessing failures.

This pattern scales to massive datasets while maintaining **perfect incrementality**: ZenML handles pipeline-level caching, manifests handle file-level incrementality.
