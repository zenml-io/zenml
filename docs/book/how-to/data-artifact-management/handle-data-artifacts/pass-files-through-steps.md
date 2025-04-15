---
description: Working with directory structures and files in ZenML pipelines.
---

# Managing Files and Directories

## Why Pass Files Between Steps?

When working with machine learning pipelines, you often need to process files stored locally on your machine. For example, you might need to:

- Process raw data files located in a specific directory
- Use configuration files for your model training
- Load pretrained model weights from a file
- Save and later reuse intermediate data processing results
- Handle files generated during data preparation steps

The `PathMaterializer` in ZenML allows you to pass these local files and directories between steps in your pipeline, making the entire workflow seamless.

## The Path Materializer

The Path Materializer is designed to handle `pathlib.Path` objects, allowing you to easily save and load both individual files and directory structures in your ZenML pipelines. This materializer preserves file contents and, in the case of directories, their complete structure.

## Key Features

- **Flexible Path Handling**: Works with both individual files and complete directory structures
- **Directory Preservation**: Stores complete directory structures, including subdirectories and files

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

2. **For Files**:
   - **Saving**: Directly stores the file in the artifact store
   - **Loading**: Copies the file to a temporary location and returns a Path object pointing to it 

## Important Considerations

Before using `Path` objects in your steps, be aware of how this works behind the scenes:

- **Artifact Storage**: When you pass a Path object from one step to another, the contents of that path are uploaded to your artifact store. This means the entire file or directory contents are copied.
- **Data Transfer**: The data will be downloaded again when consumed by downstream steps, which may impact performance when working with large files.
- **Size Limitations**: Be cautious when passing large directories or files, as this approach isn't ideal for very large datasets (multiple GB).
- **Network Bandwidth**: If your artifact store is remote (like S3 or GCS), consider network bandwidth limitations.

{% hint style="info" %}
**Version Compatibility**

The `PathMaterializer` was introduced in ZenML 0.81.0. If you have pipelines written with earlier versions, you should set the `ZENML_DISABLE_PATH_MATERIALIZER` environment variable to maintain compatibility with your existing code. This prevents the automatic registration of the `PathMaterializer` for `Path` objects.

```bash
# Set this before running pipelines developed with ZenML < 0.81.0
export ZENML_DISABLE_PATH_MATERIALIZER=true
```
{% endhint %}

For extremely large datasets, consider alternatives like:
- Using remote data access patterns within your steps 
- Passing only references to the data rather than the data itself
- Using specialized materializers for data formats that support partial reading