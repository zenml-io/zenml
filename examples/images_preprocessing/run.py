# Incremental Image Preprocessing Pipeline
# Combines external fingerprinting + ZenML caching by value + clean for loops

from typing import Annotated, List, Tuple
from pathlib import Path
import hashlib, json, time, random
import click

from PIL import Image, ImageDraw
from zenml import step, pipeline

# Configuration
N_SHARDS = 4  # Easily scalable - change to any value!
IMG_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".bmp"}

# Default paths
RAW_DIR = Path("data/raw_images") 
OUT_DIR = Path("data/outputs")

# Helper functions
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
    """Deterministic sharding - same image always goes to same shard"""
    h = hashlib.sha1(str(image_path).encode("utf-8")).hexdigest()
    return int(h, 16) % N_SHARDS

def preproc_target(base: Path, image_hash: str) -> Path:
    # Bucket files to avoid too many per directory
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

def simple_preprocess(in_path: Path, out_path: Path) -> None:
    """Example preprocessing: resize to 224x224 grayscale"""
    ensure_dir(out_path.parent)
    with Image.open(in_path) as im:
        im = im.convert("L").resize((224, 224))
        im.save(out_path)

def create_dummy_images(root: Path, count: int = 12) -> None:
    """Create test images for demo purposes"""
    ensure_dir(root)
    for i in range(count):
        im = Image.new("RGB", (256, 256), color=(random.randint(0,255), 180, 200))
        d = ImageDraw.Draw(im)
        d.text((10, 10), f"img_{i}", fill=(255, 255, 255))
        im.save(root / f"img_{i:04d}.png")

def get_directory_fingerprint(root_dir: str) -> str:
    """
    THE KEY: Compute directory fingerprint OUTSIDE the pipeline.
    This makes filesystem changes visible to ZenML's caching system.
    """
    paths = list_images_under(Path(root_dir))
    file_info = []
    for p in paths:
        mtime = p.stat().st_mtime
        size = p.stat().st_size
        file_info.append(f"{p.name}:{mtime}:{size}")
    return hashlib.md5("|".join(sorted(file_info)).encode()).hexdigest()

# ZenML Steps with proper artifact annotations
@step
def scan_images_step(
    root_dir: str, 
    dir_fingerprint: str
) -> Annotated[List[Tuple[str, str, float]], "image_metadata"]:
    """
    Scan directory for images with metadata.
    Cache invalidates when dir_fingerprint changes (filesystem changes detected).
    """
    print(f"🔍 Scanning directory with fingerprint: {dir_fingerprint[:8]}...")
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
    images_metadata: Annotated[List[Tuple[str, str, float]], "image_metadata"]
) -> Annotated[Tuple[List[Tuple[str, str, float]], ...], "sharded_metadata"]:
    """Split images into N_SHARDS based on deterministic path hashing."""
    print(f"📂 Sharding {len(images_metadata)} images into {N_SHARDS} shards")
    shards = [[] for _ in range(N_SHARDS)]
    
    for img_path, etag, mtime in images_metadata:
        shard_id = stable_shard_index(Path(img_path))
        shards[shard_id].append((img_path, etag, mtime))
    
    # Sort each shard for deterministic output
    for shard in shards:
        shard.sort()
    
    shard_sizes = [len(shard) for shard in shards]
    print(f"Shard sizes: {shard_sizes}")
    
    return tuple(shards)

@step
def extract_shard_step(
    shards: Annotated[Tuple[List[Tuple[str, str, float]], ...], "sharded_metadata"], 
    shard_id: int
) -> Annotated[List[Tuple[str, str, float]], "shard_metadata"]:
    """Extract a specific shard by ID."""
    shard_data = shards[shard_id]
    print(f"🎯 Extracting shard {shard_id}: {len(shard_data)} images")
    return shard_data

@step
def preprocess_shard_step(
    shard_id: int,
    shard_metadata: Annotated[List[Tuple[str, str, float]], "shard_metadata"],
    out_dir: str,
) -> Annotated[str, "manifest_path"]:
    """
    Process shard with incremental logic and manifest tracking.
    
    KEY INSIGHT: With ZenML's caching by value, if the shard content 
    is unchanged, this step will be cached even if upstream steps rerun!
    
    Returns manifest path (string) to enable caching by value.
    """
    print(f"⚙️  Processing shard {shard_id}")
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
    print(f"  [shard {shard_id}] total={len(shard_metadata)} new={num_new} skipped={num_skipped}")
    
    # Return manifest path - enables caching by value
    return str(mpath)

@step
def summarize_results_step(
    out_dir: str
) -> Annotated[int, "total_processed_count"]:
    """Count total processed files from all manifests."""
    outputs = []
    for i in range(N_SHARDS):
        mpath = manifest_path(Path(out_dir), i)
        if mpath.exists():
            data = load_manifest(mpath)
            outputs.extend(v["output"] for v in data.values())
    
    total = len(set(outputs))
    print(f"📊 [summary] Total preprocessed files across all shards: {total}")
    return total

# The Perfect Pipeline
@pipeline
def incremental_preproc_pipeline(
    root_dir: str, 
    out_dir: str, 
    dir_fingerprint: str
) -> Annotated[int, "pipeline_total_processed"]:
    """
    Perfect incremental processing pipeline combining:
    
    ✅ External fingerprinting (breaks cache when filesystem changes)
    ✅ Clean for loop (scalable to any N_SHARDS) 
    ✅ ZenML caching by value (caches unchanged shards automatically)
    ✅ Manifest-based incrementality (only processes new/changed images)
    """
    # Scan and shard images
    images_metadata = scan_images_step(root_dir, dir_fingerprint)
    shards = shard_images_step(images_metadata)
    
    # Process each shard with clean for loop - truly scalable!
    for i in range(N_SHARDS):
        shard_data = extract_shard_step(shards, shard_id=i)
        preprocess_shard_step(shard_id=i, shard_metadata=shard_data, out_dir=out_dir)
    
    # Optional: summarize results
    total_files = summarize_results_step(out_dir)
    return total_files

# CLI Interface
@click.command()
@click.option(
    "--raw-dir", 
    default=str(RAW_DIR),
    help=f"Directory containing raw images (default: {RAW_DIR})"
)
@click.option(
    "--out-dir",
    default=str(OUT_DIR), 
    help=f"Output directory for processed images (default: {OUT_DIR})"
)
@click.option(
    "--create-dummy",
    is_flag=True,
    help="Create dummy test images if raw directory doesn't exist"
)
@click.option(
    "--shards",
    default=N_SHARDS,
    help=f"Number of shards to split images into (default: {N_SHARDS})"
)
def main(raw_dir: str, out_dir: str, create_dummy: bool, shards: int):
    """
    Run incremental image preprocessing pipeline.
    
    This pipeline demonstrates perfect incrementality - only new/changed 
    images are processed while leveraging ZenML's intelligent caching.
    """
    global N_SHARDS
    N_SHARDS = shards
    
    raw_path = Path(raw_dir)
    out_path = Path(out_dir)
    
    # Create dummy images if requested and directory doesn't exist
    if create_dummy and not raw_path.exists():
        create_dummy_images(raw_path, count=12)
        print(f"✨ Created dummy images in: {raw_path.resolve()}")
    
    if not raw_path.exists():
        print(f"❌ Raw directory {raw_path} doesn't exist!")
        print("💡 Use --create-dummy to create test images")
        return
    
    print(f"🚀 Running incremental preprocessing pipeline:")
    print(f"   📁 Raw images: {raw_path}")
    print(f"   📁 Output: {out_path}")
    print(f"   🔢 Shards: {shards}")
    
    # THE KEY: Compute directory fingerprint OUTSIDE the pipeline
    dir_fingerprint = get_directory_fingerprint(raw_dir)
    print(f"   🔍 Directory fingerprint: {dir_fingerprint[:8]}...")
    
    # Run the pipeline
    result = incremental_preproc_pipeline(raw_dir, out_dir, dir_fingerprint)
    
    print(f"\n🎉 Pipeline completed!")
    print(f"📁 Results stored in:")
    print(f"   • Manifests: {out_path}/manifests/shard_*.json") 
    print(f"   • Processed images: {out_path}/preproc/<bucket>/<hash>.png")
    print(f"\n💡 Try adding a new image and running again - only 1 shard will reprocess!")

if __name__ == "__main__":
    main()