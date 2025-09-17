# Incremental Image Preprocessing with ZenML

This example demonstrates how to build a scalable, incremental image preprocessing pipeline using ZenML's caching system and external directory fingerprinting.

## What you'll learn

- How to implement incremental processing for large image datasets
- Leverage ZenML's **caching by value** for optimal performance
- Use external directory fingerprinting to detect filesystem changes
- Build fan-out/fan-in patterns with clean for loops that scale to any number of shards
- Combine ZenML's intelligent caching with manifest-based incrementality

## The Problem

When your dataset of images grows, feeding the **entire list** into one preprocessing step makes ZenML's cache invalidate on every tiny change. If you have 1000 images and add just 1 new image, you don't want to reprocess all 1000 images again.

## The Solution

This example shows a practical pattern to **only preprocess new/changed images** using:

1. **External directory fingerprinting** - Makes filesystem changes visible to ZenML's caching
2. **Deterministic sharding** - Splits images into stable shards so adding one file only affects one shard  
3. **ZenML's caching by value** - Automatically caches unchanged shards even when scan step reruns
4. **Manifest-based incrementality** - Tracks processed files per shard and skips already-processed images
5. **Clean for loop** - Scalable code that works for any `N_SHARDS`

## How it Works

```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│ Raw Images Folder   │───▶│ External Fingerprint │───▶│ Directory Changed?  │
│ /data/raw_images/   │    │ (mtime + size hash)  │    │ Cache break or use? │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
                                                                      │
                           ┌─────────────────────────────────────────┘
                           ▼
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│ Scan Images Step    │───▶│ Shard Images Step    │───▶│ Process Each Shard  │
│ List all images     │    │ Split into N shards  │    │ for i in range(N)   │
│ with MD5 + mtime    │    │ by path hash         │    │ ├─ Extract shard    │
└─────────────────────┘    └──────────────────────┘    │ ├─ Check manifest   │
                                                        │ ├─ Process new only │
                                                        │ └─ Update manifest │
                                                        └─────────────────────┘
```

## Key Features

✅ **Perfect incrementality**: Only processes new/changed images  
✅ **Selective caching**: Unchanged shards stay cached while affected shards recompute  
✅ **Scalable sharding**: Clean `for i in range(N_SHARDS)` - change N to any value  
✅ **Deterministic placement**: Same image always goes to same shard  
✅ **Content-based deduplication**: Uses MD5 hashes to avoid processing duplicates  
✅ **Robust change detection**: External fingerprinting catches all filesystem changes  

## Quick Start

```bash
# Install requirements
pip install zenml pillow

# Run the pipeline
python run.py

# Add a new image and run again - only 1 shard will reprocess!
python -c "
from PIL import Image
Image.new('RGB', (256, 256), color=(255, 0, 0)).save('data/raw_images/new_image.png')
"
python run.py
```

## What You'll See

**First run**: Processes all images
```
🔍 Scanning directory with fingerprint: a1b2c3d4...
Found 12 images
⚙️ PROCESSING SHARD 0: total=3 new=3 skipped=0
⚙️ PROCESSING SHARD 1: total=3 new=3 skipped=0  
⚙️ PROCESSING SHARD 2: total=3 new=3 skipped=0
⚙️ PROCESSING SHARD 3: total=3 new=3 skipped=0
```

**Second run** (after adding 1 image):
```
🔍 Scanning directory with fingerprint: e5f6g7h8... (changed!)
Found 13 images  
Using cached version of step preprocess_shard_step (shard 0) ✅
Using cached version of step preprocess_shard_step (shard 1) ✅
⚙️ PROCESSING SHARD 2: total=4 new=1 skipped=3 ⚡
Using cached version of step preprocess_shard_step (shard 3) ✅
```

**Perfect!** Only shard 2 recomputed because that's where the new image was placed.

## Technical Deep Dive

### External Directory Fingerprinting
```python
def get_directory_fingerprint(root_dir: str) -> str:
    """Makes filesystem changes visible to ZenML's caching system"""
    paths = list_images_under(Path(root_dir))
    file_info = []
    for p in paths:
        mtime = p.stat().st_mtime
        size = p.stat().st_size
        file_info.append(f"{p.name}:{mtime}:{size}")
    return hashlib.md5("|".join(sorted(file_info)).encode()).hexdigest()
```

### ZenML's Caching by Value
ZenML automatically caches steps that return the same primitive values (strings, integers, etc.). If a shard's content doesn't change, its processing step will be cached even if upstream steps rerun.

### Deterministic Sharding  
```python
def stable_shard_index(image_path: Path) -> int:
    """Same image always goes to same shard"""
    h = hashlib.sha1(str(image_path).encode("utf-8")).hexdigest()
    return int(h, 16) % N_SHARDS
```

### Manifest-Based Incrementality
Each shard maintains a JSON manifest tracking processed files:
```json
{
  "path/to/image.png": {
    "etag": "md5hash",
    "output": "path/to/processed.png", 
    "processed_at": 1234567890
  }
}
```

## Configuration

Edit these variables in `run.py`:

- `N_SHARDS`: Number of shards (4, 8, 16, 32, 64, 128, etc.)
- `RAW_DIR`: Input image directory
- `OUT_DIR`: Output directory for processed images and manifests

## Production Considerations

- **Parallelism**: Use remote orchestrators (Kubernetes/SSH) to process shards in parallel
- **Storage**: Consider manifest storage location for team workflows  
- **Monitoring**: Pipeline logs show exactly what's cached vs recomputed
- **Error handling**: Add retry logic for transient preprocessing failures
- **Scalability**: Tested with 1000+ images, scales to massive datasets

## Further Exploration

This example demonstrates core ZenML concepts:
- [Pipeline caching](https://docs.zenml.io/user-guides/starter-guide/cache-previous-executions)
- [Artifacts and metadata](https://docs.zenml.io/user-guides/starter-guide/manage-artifacts)
- [Custom steps](https://docs.zenml.io/user-guides/pipelines-and-steps/steps)

Ready to scale your image processing workflows? The pattern shown here works for any file-based processing task where you need perfect incrementality combined with intelligent caching!