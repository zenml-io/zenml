---
description: Working with directory structures and files in ZenML pipelines.
---

# Managing Files and Directories

The Path Materializer is designed to handle `pathlib.Path` objects, allowing you to easily save and load directory structures in your ZenML pipelines. This materializer treats a directory as a complete artifact, preserving its structure and file contents.

## Key Features

- **Directory Preservation**: Stores complete directory structures, including subdirectories and files
- **Interactive Visualization**: Provides an HTML visualization with file directory listing
- **Direct Download Links**: Allows downloading individual files directly from the visualization
- **Text File Preview**: Enables previewing text-based files within the visualization
- **Detailed Metadata**: Extracts useful metadata like file counts, size statistics, and extension distribution

## Example Usage

Here's how you can use the Path Materializer in your ZenML pipelines:

```python
from pathlib import Path
import os
from zenml import step, pipeline
from zenml.materializers import PathMaterializer

# Step that creates and returns a directory
@step
def create_directory() -> Path:
    # Create a temporary directory with some files
    temp_dir = Path("./my_data_directory")
    temp_dir.mkdir(exist_ok=True)
    
    # Add some files
    (temp_dir / "data.csv").write_text("id,value\n1,100\n2,200\n3,300")
    (temp_dir / "config.json").write_text('{"name": "test", "value": 42}')
    
    # Create a subdirectory with more files
    models_dir = temp_dir / "models"
    models_dir.mkdir(exist_ok=True)
    (models_dir / "model.txt").write_text("This is a model file")
    
    return temp_dir

# Step that uses the directory
@step
def use_directory(dir_path: Path):
    print(f"Directory path: {dir_path}")
    print(f"Contents: {os.listdir(dir_path)}")
    
    # Read some files
    data_file = dir_path / "data.csv"
    print(f"Data file contents:\n{data_file.read_text()}")
    
    # Access subdirectories
    models_dir = dir_path / "models"
    print(f"Models dir contents: {os.listdir(models_dir)}")

# Define and run the pipeline
@pipeline
def directory_pipeline():
    dir_path = create_directory()
    use_directory(dir_path)

# Run the pipeline
directory_pipeline()
```

The Path Materializer will automatically be used for any `pathlib.Path` objects in your pipeline steps.

## How It Works

Under the hood, the Path Materializer:

1. **Saving**: Compresses the directory into a `.tar.gz` archive and stores it in the artifact store
2. **Loading**: Extracts the archive to a temporary directory and returns a Path object pointing to it
3. **Visualization**: Creates an HTML page with the directory structure and file contents for interactive browsing

## Metadata

The Path Materializer extracts the following metadata:

- `path`: Original path of the directory
- `file_count`: Total number of files in the directory (including subdirectories)
- `directory_count`: Number of subdirectories
- `total_size_bytes`: Total size of all files in bytes
- `file_extensions`: Dictionary of file extensions and their frequencies 