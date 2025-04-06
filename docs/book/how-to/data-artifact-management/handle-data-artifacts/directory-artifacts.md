---
description: Working with directory structures and files in ZenML pipelines.
---

# Managing Files and Directories

The Path Materializer is designed to handle `pathlib.Path` objects, allowing you to easily save and load both individual files and directory structures in your ZenML pipelines. This materializer preserves file contents and, in the case of directories, their complete structure.

## Key Features

- **Flexible Path Handling**: Works with both individual files and complete directory structures
- **Directory Preservation**: Stores complete directory structures, including subdirectories and files
- **Interactive Visualization**: Provides an HTML visualization with file content or directory listing
- **Direct Download Links**: Allows downloading files directly from the visualization
- **Text File Preview**: Enables previewing text-based files within the visualization
- **Detailed Metadata**: Extracts useful metadata like size, file type, or directory statistics

## Example Usage

Here's how you can use the Path Materializer in your ZenML pipelines:

### Working with Directories

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

### Working with Individual Files

```python
from pathlib import Path
from zenml import step, pipeline

# Step that creates and returns a file
@step
def create_file() -> Path:
    # Create a file with some content
    file_path = Path("./data.txt")
    file_path.write_text("This is a test file with important data")
    return file_path

# Step that uses the file
@step
def use_file(file_path: Path):
    print(f"File path: {file_path}")
    print(f"File content: {file_path.read_text()}")
    print(f"File size: {file_path.stat().st_size} bytes")

# Define and run the pipeline
@pipeline
def file_pipeline():
    file_path = create_file()
    use_file(file_path)

# Run the pipeline
file_pipeline()
```

The Path Materializer will automatically be used for any `pathlib.Path` objects in your pipeline steps, whether they represent files or directories.

## How It Works

Under the hood, the Path Materializer:

1. **For Directories**:
   - **Saving**: Compresses the directory into a `.tar.gz` archive and stores it in the artifact store
   - **Loading**: Extracts the archive to a temporary directory and returns a Path object pointing to it
   - **Visualization**: Creates an HTML page with the directory structure and file contents for interactive browsing

2. **For Files**:
   - **Saving**: Directly stores the file in the artifact store
   - **Loading**: Copies the file to a temporary location and returns a Path object pointing to it
   - **Visualization**: Creates an HTML page with file information, download option, and content preview for text files

## Metadata

The Path Materializer extracts the following metadata:

### For Directories:
- `path`: Original path of the directory
- `file_count`: Total number of files in the directory (including subdirectories)
- `directory_count`: Number of subdirectories
- `total_size_bytes`: Total size of all files in bytes
- `file_extensions`: Dictionary of file extensions and their frequencies

### For Files:
- `path`: Original path of the file
- `file_name`: Name of the file
- `file_extension`: Extension of the file
- `file_size_bytes`: Size of the file in bytes
- `is_text`: Boolean indicating whether the file is a text file 